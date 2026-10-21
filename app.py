import os
import time
import json
import math
import re
import unicodedata
import atexit
import asyncio
import numpy as np
import torch
import torch.nn.functional as F
import base64
import io
import wave
import requests
from collections import OrderedDict
from datetime import datetime, timezone
from piper.voice import PiperVoice
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt

from src.features import FEATURE_SIZE, add_hand_local_features, hand_present
from src.model.lstm import SignLanguageLSTM
import storage
from capture_validation import (
    validate_audit_payload,
    validate_capture_blendshapes,
    validate_capture_label,
    validate_frames,
    validate_report_payload,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Nexora LSA-64 API")

# RNF-T-06: only the configured local-network origins (comma-separated env var).
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "NEXORA_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Per-stage telemetry (LATENCY_V2_TIMING: off | stdout | jsonl)
# ---------------------------------------------------------------------------
TIMING_MODE = os.environ.get("LATENCY_V2_TIMING", "off").lower()
TIMING_ENDPOINT_ENABLED = (
    os.environ.get("LATENCY_V2_TIMING_ENDPOINT", "false").lower() == "true"
)
TIMING_FILE_PATH = "timings.jsonl"
TIMING_STREAM_MAX_LINES = 1000
TIMING_FILE_HANDLE = None
TIMING_CYCLE_COUNTER = 0
TIMING_FIELDS = (
    "lstm_ms",
    "translation_ms",
    "tts_ms",
    "total_ms",
)


def _timing_open_sink():
    global TIMING_FILE_HANDLE
    if TIMING_FILE_HANDLE is not None:
        return True
    try:
        TIMING_FILE_HANDLE = open(TIMING_FILE_PATH, "a", encoding="utf-8", buffering=1)
        return True
    except Exception as e:
        print(f"[Nexora timing] failed to open {TIMING_FILE_PATH}: {e}")
        return False


def _timing_close_sink():
    global TIMING_FILE_HANDLE
    if TIMING_FILE_HANDLE is not None:
        try:
            TIMING_FILE_HANDLE.close()
        finally:
            TIMING_FILE_HANDLE = None


def _timing_next_cycle_id():
    global TIMING_CYCLE_COUNTER
    TIMING_CYCLE_COUNTER += 1
    return TIMING_CYCLE_COUNTER


def _timing_emit_cycle(record: dict):
    if TIMING_MODE == "off":
        return
    if TIMING_MODE == "stdout":
        parts = []
        for k in TIMING_FIELDS:
            if k in record:
                parts.append(f"{k}={record[k]}")
        if "cycle_id" in record:
            parts.insert(0, f"cycle={record['cycle_id']}")
        if "top3_count" in record:
            parts.append(f"top3={record['top3_count']}")
        if "source" in record:
            parts.append(f"source={record['source']}")
        print("[Nexora timing] " + " ".join(parts))
    elif TIMING_MODE == "jsonl":
        if _timing_open_sink():
            try:
                TIMING_FILE_HANDLE.write(json.dumps(record) + "\n")
            except Exception as e:
                print(f"[Nexora timing] write failed: {e}")


def _stream_timings_tail():
    try:
        with open(TIMING_FILE_PATH, "rb") as f:
            tail = f.readlines()[-TIMING_STREAM_MAX_LINES:]
        for line in tail:
            yield line
    except FileNotFoundError:
        return
    except Exception as e:
        print(f"[Nexora timing] stream failed: {e}")
        return


atexit.register(_timing_close_sink)

# ---------------------------------------------------------------------------
# Load model once at startup
# ---------------------------------------------------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

LSTM_MAX_FRAMES = int(os.environ.get("LSTM_MAX_FRAMES", "45"))
WS_RECEIVE_TIMEOUT_MS = int(os.environ.get("WS_RECEIVE_TIMEOUT_MS", "5000"))
LSTM_MODEL_PATH = "models/lstm.pth"
LSTM_CLASSES_PATH = "models/custom_classes.json"

if not os.path.exists(LSTM_MODEL_PATH) or not os.path.exists(LSTM_CLASSES_PATH):
    print("[Nexora] ATENCIÓN: No se encontraron los archivos del modelo LSTM. Por favor graba datos y entrena el modelo.")
    CLASSES = []
    model = None
    MAX_FRAMES = LSTM_MAX_FRAMES
else:
    with open(LSTM_CLASSES_PATH, "r", encoding="utf-8") as f:
        CLASSES = json.load(f)

    model = SignLanguageLSTM(num_classes=len(CLASSES), input_size=FEATURE_SIZE).to(device)
    model.load_state_dict(torch.load(LSTM_MODEL_PATH, map_location=device, weights_only=False))
    model.eval()
    MAX_FRAMES = LSTM_MAX_FRAMES
    print(f"[Nexora] Custom LSTM Model loaded on {device} — {len(CLASSES)} classes — {MAX_FRAMES} frames ({LSTM_MODEL_PATH})")

PIPER_MODEL_PATH = "voices/es_AR-daniela-high.onnx"
if os.path.exists(PIPER_MODEL_PATH):
    try:
        piper_voice = PiperVoice.load(PIPER_MODEL_PATH)
        # Warm up TTS to avoid cold-start latency on first real request
        _warmup_buf = io.BytesIO()
        with wave.open(_warmup_buf, "wb") as _wf:
            _wf.setnchannels(1)
            _wf.setsampwidth(2)
            _wf.setframerate(piper_voice.config.sample_rate)
            piper_voice.synthesize_wav("ok", _wf)
        del _warmup_buf
        print("[Nexora] Piper TTS Model loaded (warmed up)")
    except Exception as e:
        print(f"[Nexora] Error loading Piper TTS: {e}")
        piper_voice = None
else:
    piper_voice = None
    print("[Nexora] Piper TTS Model not found")

# ---------------------------------------------------------------------------
# Medical phrase templates — bypass LLM for known word combinations
# ---------------------------------------------------------------------------
# Key: frozenset of normalized words (order-independent matching)
# Value: natural sentence in Argentine Spanish
MEDICAL_TEMPLATES: dict[frozenset[str], str] = {
    # Single words
    frozenset({"dolor"}): "Tengo dolor.",
    frozenset({"ayuda"}): "Necesito ayuda.",
    frozenset({"doctor"}): "Necesito un doctor.",
    frozenset({"respirar"}): "No puedo respirar bien.",
    frozenset({"revisar"}): "Necesito que me revisen.",
    # Two-word combos
    frozenset({"dolor", "ayuda"}): "Tengo dolor, necesito ayuda.",
    frozenset({"dolor", "doctor"}): "Tengo dolor, necesito un doctor.",
    frozenset({"dolor", "respirar"}): "Tengo dolor al respirar.",
    frozenset({"ayuda", "doctor"}): "Necesito ayuda del doctor.",
    frozenset({"ayuda", "respirar"}): "Necesito ayuda, no puedo respirar.",
    frozenset({"doctor", "revisar"}): "Necesito que el doctor me revise.",
    frozenset({"doctor", "respirar"}): "Doctor, no puedo respirar.",
    frozenset({"ayuda", "revisar"}): "Necesito ayuda, que me revisen.",
    frozenset({"dolor", "revisar"}): "Tengo dolor, necesito que me revisen.",
    frozenset({"respirar", "revisar"}): "No puedo respirar bien, necesito que me revisen.",
    # Three-word combos
    frozenset({"dolor", "ayuda", "doctor"}): "Tengo dolor, necesito ayuda del doctor.",
    frozenset({"dolor", "doctor", "respirar"}): "Doctor, tengo dolor al respirar.",
    frozenset({"ayuda", "doctor", "respirar"}): "Necesito ayuda del doctor, no puedo respirar.",
    frozenset({"dolor", "ayuda", "respirar"}): "Tengo dolor y no puedo respirar, necesito ayuda.",
    frozenset({"dolor", "doctor", "revisar"}): "Tengo dolor, necesito que el doctor me revise.",
    frozenset({"ayuda", "doctor", "revisar"}): "Necesito ayuda, que el doctor me revise.",
    frozenset({"dolor", "ayuda", "revisar"}): "Tengo dolor, necesito ayuda y que me revisen.",
    frozenset({"dolor", "respirar", "revisar"}): "Tengo dolor al respirar, necesito que me revisen.",
    frozenset({"ayuda", "respirar", "revisar"}): "Necesito ayuda, no puedo respirar y necesito que me revisen.",
    frozenset({"doctor", "respirar", "revisar"}): "Doctor, no puedo respirar, necesito que me revise.",
    # Casos demo/video
    frozenset({"cabeza", "dolor"}): "Tengo dolor de cabeza.",
    frozenset({"yo", "cabeza", "dolor"}): "Me duele la cabeza.",
    frozenset({"yo", "cabeza", "dolor", "respirar"}): "Me duele la cabeza y me cuesta respirar.",
    frozenset({"cabeza", "dolor", "respirar"}): "Tengo dolor de cabeza al respirar.",
    # Trainable 5-class combinations (head, dolor, respirar, yo). idle excluded by _match_template.
    frozenset({"cabeza"}): "Tengo algo en la cabeza.",
    frozenset({"yo"}): "Necesito comunicar algo.",
    frozenset({"cabeza", "respirar"}): "Me cuesta respirar, me duele la cabeza.",
    frozenset({"cabeza", "yo"}): "Necesito hablar sobre mi cabeza.",
    frozenset({"dolor", "yo"}): "Tengo dolor.",
    frozenset({"respirar", "yo"}): "No puedo respirar bien.",
    frozenset({"cabeza", "dolor", "yo"}): "Me duele la cabeza.",
    frozenset({"cabeza", "respirar", "yo"}): "Mi cabeza y mi respiración no están bien.",
    frozenset({"dolor", "respirar", "yo"}): "Tengo dolor y no puedo respirar bien.",
    frozenset({"cabeza", "dolor", "respirar", "yo"}): "Me duele la cabeza, no puedo respirar bien.",
}

LATENCY_V2_UNREACHABLE_TOKENS = ("ayuda", "doctor", "revisar")
TRAINABLE_HEAD_TOKENS = ("cabeza", "dolor", "respirar", "yo")
TRAINABLE_NEW_TEMPLATE_COUNT = 2 ** len(TRAINABLE_HEAD_TOKENS) - 1

print(
    f"[Nexora] MEDICAL_TEMPLATES: {TRAINABLE_NEW_TEMPLATE_COUNT} trainable combos "
    f"covered ({len(TRAINABLE_HEAD_TOKENS)} tokens); unreachable entries for "
    f"{'/'.join(LATENCY_V2_UNREACHABLE_TOKENS)} kept for forward compatibility."
)


def _normalize_words(words: str) -> str:
    """Lowercase, deduplicate, remove 'idle', sort — stable cache key."""
    tokens = words.lower().split()
    unique = list(dict.fromkeys(t for t in tokens if t != "idle"))
    return " ".join(sorted(unique))


def _match_template(words: str) -> str | None:
    """Try to match words against known medical templates."""
    tokens = words.lower().split()
    meaningful = frozenset(t for t in tokens if t != "idle")
    if not meaningful:
        return None
    return MEDICAL_TEMPLATES.get(meaningful)


# ---------------------------------------------------------------------------
# Clinical fidelity check (RF-01.8) — deterministic guard on the LLM sentence
# ---------------------------------------------------------------------------
NO_CLARO = "NO_CLARO"  # the only non-sentence value the frontend discards

# Whitelist: every word of the LLM sentence must come from the input, from a synonym group
# the input touches, or from this closed set of grammar words. Negations, pronouns, numbers
# and intensifiers are deliberately absent: they are allowed only when they were signed.
# A false rejection costs only the raw-words fallback, which is faithful by construction.
SYNONYM_GROUPS = (
    ("dolor", "duel"), ("respir",), ("estomag", "panza"), ("fiebre", "febr"),
    ("medicament", "pastilla"), ("doctor", "medico"), ("ayud",),
)
GRAMMAR_WORDS = frozenset(
    "me te le se lo la los las el un una de del en a al y o e mi mis su sus que con por para "
    "tengo tiene tenes siento siente estoy esta cuesta cuestan puedo puede hay es".split()
)
PROMPT_LEAK_RE = re.compile(r"[()\[\]\n]|NO[ _]agregues|NO_CLARO|Traducci[oó]n|Palabras a traducir|REGLA", re.I)


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))


def _is_faithful(sentence: str, words: str) -> bool:
    """True if the sentence is a single clean sentence built only from the input words (see GRAMMAR_WORDS)."""
    if PROMPT_LEAK_RE.search(sentence) or len(re.findall(r"[.!?]\s*\S", sentence)) > 0:
        return False
    in_tokens = [t for t in re.findall(r"\w+", _strip_accents(words)) if t != "idle"]
    stems = [t[:4] if len(t) >= 4 else t for t in in_tokens]
    stems += [s for group in SYNONYM_GROUPS if any(t.startswith(group) for t in in_tokens) for s in group]

    def allowed(t: str) -> bool:
        return t in GRAMMAR_WORDS or t in in_tokens or any(len(s) >= 4 and t.startswith(s) for s in stems)

    return all(allowed(t) for t in re.findall(r"\w+", _strip_accents(sentence)))


# ---------------------------------------------------------------------------
# LRU caches — translation & TTS audio
# ---------------------------------------------------------------------------
MAX_TRANSLATION_CACHE = 200
MAX_AUDIO_CACHE = 50

_translation_cache: OrderedDict[str, str] = OrderedDict()
_audio_cache: OrderedDict[str, str] = OrderedDict()  # sentence -> base64


def _cache_get(cache: OrderedDict, key: str):
    """Get from LRU cache, moving to end on hit."""
    if key in cache:
        cache.move_to_end(key)
        return cache[key]
    return None


def _cache_put(cache: OrderedDict, key: str, value: str, max_size: int):
    """Put into LRU cache, evicting oldest if full."""
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > max_size:
        cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class SkeletonPayload(BaseModel):
    # List of frames; each frame is a list of 75 landmarks [x, y, z, visibility]
    frames: list[list[list[float]]]

class CapturePayload(BaseModel):
    label: str
    frames: list[list[list[float]]]
    blendshapes: list[list[float]] | None = None

class SentencePayload(BaseModel):
    words: str

class ReportPayload(BaseModel):
    text: str
    station: str
    words: list[str] | None = None
    message_id: StrictInt | StrictBool | None = None  # strict: bool/str must not be coerced; bool reaches validate_report_payload


def _prepare_input(data: np.ndarray) -> np.ndarray:
    T = data.shape[0]
    if T > MAX_FRAMES:
        data = data[-MAX_FRAMES:]
    elif T < MAX_FRAMES:
        # Short windows (e.g. right after the camera starts) are front-padded with the oldest frame,
        # as if the person stood still before it. Zero padding is unseen in training: an idle window
        # padded with zeros scored ~96% dolor.
        data = np.concatenate((np.repeat(data[:1], MAX_FRAMES - T, axis=0), data), axis=0)
    return add_hand_local_features(data, hand_present(data))


def _infer(data: np.ndarray) -> tuple[dict, float]:
    """(T, 75, 4) validated frames -> ({sign, confidence, top3}, lstm_ms). Shared by /predict and the WS."""
    lstm_t0 = time.perf_counter()
    # Nobody in front of the camera is idle by definition: the model never saw empty scenes and
    # would guess a sign (an all-zero window scores ~80% dolor).
    if (data[:, 11:23, 3].max(axis=1) > 0).mean() < 0.5:
        top3 = [{"sign": "idle", "confidence": 100.0}]
        return {"sign": "idle", "confidence": 100.0, "top3": top3}, (time.perf_counter() - lstm_t0) * 1000.0

    input_tensor = torch.tensor(_prepare_input(data), dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = F.softmax(model(input_tensor), dim=1)
        confidence, predicted_idx = torch.max(probs, 1)

    top3_probs, top3_idx = torch.topk(probs, 3, dim=1)
    top3 = [
        {"sign": CLASSES[i.item()], "confidence": round(p.item() * 100, 2)}
        for p, i in zip(top3_probs[0], top3_idx[0])
    ]
    result = {
        "sign": CLASSES[predicted_idx.item()],
        "confidence": round(confidence.item() * 100, 2),
        "top3": top3,
    }
    return result, (time.perf_counter() - lstm_t0) * 1000.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
os.makedirs("dataset/custom", exist_ok=True)
DB_PATH = storage.DEFAULT_DB_PATH
storage.init_db(DB_PATH)


def _log_audit(event_type: str, **fields) -> None:
    """Best-effort audit write: an audit failure must never break the primary operation."""
    try:
        storage.log_audit_event(DB_PATH, event_type, **fields)
    except Exception as e:
        print(f"[Nexora] Audit write failed ({event_type}): {e}")


def _percentile(sorted_values: list[float], pct: float) -> float:
    n = len(sorted_values)
    idx = min(n - 1, max(0, math.ceil(pct / 100 * n) - 1))
    return sorted_values[idx]


def _latency_summary(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "p50": round(_percentile(ordered, 50), 2),
        "p95": round(_percentile(ordered, 95), 2),
        "max": round(ordered[-1], 2),
        "count": len(ordered),
    }

@app.get("/")
def health():
    return {"status": "ok", "device": str(device), "classes": len(CLASSES)}

@app.get("/classes")
def get_classes():
    return CLASSES


@app.get("/dataset_stats")
def dataset_stats():
    stats = {}
    base_dir = os.path.join("dataset", "custom")
    if os.path.exists(base_dir):
        for label in os.listdir(base_dir):
            label_dir = os.path.join(base_dir, label)
            if os.path.isdir(label_dir):
                stats[label] = len([f for f in os.listdir(label_dir) if f.endswith('.npy')])
    return stats


@app.post("/capture")
def capture(payload: CapturePayload):
    if len(payload.frames) < 5:
        raise HTTPException(status_code=400, detail="Too few frames (min 5)")

    try:
        validate_capture_label(payload.label)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    T = len(payload.frames)

    try:
        data = validate_frames(payload.frames)
        blendshapes_arr = validate_capture_blendshapes(T, payload.blendshapes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    timestamp = int(time.time() * 1000)
    label_dir = os.path.join("dataset", "custom", payload.label)
    os.makedirs(label_dir, exist_ok=True)
    filename = os.path.join(label_dir, f"{timestamp}.npy")
    np.save(filename, data)

    blendshapes_dir = os.path.join("dataset", "custom_blendshapes", payload.label)
    os.makedirs(blendshapes_dir, exist_ok=True)
    np.save(os.path.join(blendshapes_dir, f"{timestamp}.npy"), blendshapes_arr)

    count = len(os.listdir(label_dir))
    return {"status": "ok", "saved_to": filename, "samples_for_label": count}


@app.post("/report")
def report_translation(payload: ReportPayload):
    try:
        validate_report_payload(payload.text, payload.station, payload.words, payload.message_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    saved = storage.save_report(
        DB_PATH,
        text=payload.text,
        station=payload.station,
        words=payload.words,
        client_message_id=payload.message_id,
    )
    _log_audit("report", station=payload.station)

    return {"status": "ok", "report_id": saved["report_id"], "message_id": saved["message_id"]}


@app.get("/reports/summary")
def reports_summary(limit: int = 10):
    return storage.report_summary(DB_PATH, limit=max(1, min(limit, 100)))


class AuditPayload(BaseModel):
    type: str
    station: str
    consent: str | None = None
    e2e_ms: StrictInt | StrictFloat | None = None


@app.post("/audit")
def audit_event(payload: AuditPayload):
    try:
        validate_audit_payload(payload.type, payload.station, payload.consent, payload.e2e_ms)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fields = {"station": payload.station}
    if payload.type == "consent":
        fields["consent"] = payload.consent
    elif payload.type == "translation_displayed":
        fields["e2e_ms"] = round(payload.e2e_ms, 2)
    # Strict: recording the event is this endpoint's whole purpose, so failures reach the caller.
    storage.log_audit_event(DB_PATH, payload.type, **fields)

    return {"status": "ok"}


@app.get("/metrics")
def metrics(since: str | None = None):
    since_dt = None
    if since:
        try:
            # Python 3.10 fromisoformat rejects the 'Z' suffix (Date.toISOString format)
            since_dt = datetime.fromisoformat(since[:-1] + "+00:00" if since.endswith("Z") else since)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid since timestamp")
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

    aggregated = storage.audit_metrics(DB_PATH, since_dt)
    counts = aggregated["counts"]

    latency_stats = {
        field: _latency_summary(values)
        for field, values in aggregated["latency_samples"].items()
        if values
    }

    return {
        "counts": counts,
        "consent": aggregated["consent"],
        "reports": counts.get("report", 0),
        "translation_source": aggregated["sources"],
        "latency_ms": latency_stats,
    }


@app.post("/predict")
def predict(payload: SkeletonPayload):
    if len(payload.frames) < 5:
        raise HTTPException(status_code=400, detail="Too few frames (min 5)")

    if model is None:
        raise HTTPException(status_code=500, detail="Modelo no entrenado. Por favor entrena el LSTM primero.")

    try:
        data = validate_frames(payload.frames)  # (T, 75, 4)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result, lstm_ms = _infer(data)
    _log_audit("prediction", lstm_ms=round(lstm_ms, 2), confidence=result["confidence"])

    if TIMING_MODE != "off":
        cycle_id = _timing_next_cycle_id()
        _timing_emit_cycle({
            "cycle_id": cycle_id,
            "lstm_ms": round(lstm_ms, 2),
            "total_ms": round(lstm_ms, 2),
            "top3_count": len(result["top3"]),
            "source": "predict",
        })

    return result

@app.websocket("/ws/predict")
async def websocket_predict(websocket: WebSocket):
    # Browsers always send Origin; a missing one means a non-browser client (no CSWSH risk).
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1008)  # rejected before accept -> HTTP 403
        return
    await websocket.accept()
    if model is None:
        await websocket.close(code=1011, reason="Modelo no entrenado")
        return

    proto_version = websocket.query_params.get("v", "1").lower()

    try:
        while True:
            try:
                data_np = None
                if proto_version == "2":
                    try:
                        payload = await asyncio.wait_for(
                            websocket.receive_bytes(),
                            timeout=WS_RECEIVE_TIMEOUT_MS / 1000,
                        )
                    except asyncio.TimeoutError:
                        await websocket.send_json({"error": "receive timeout"})
                        continue
                    if len(payload) < 4:
                        await websocket.send_json({"error": "binary header too short"})
                        continue
                    if payload[0] != 0x02:
                        await websocket.send_json({"error": "unsupported binary version"})
                        continue
                    landmarks_per_frame = 75
                    floats_per_frame = landmarks_per_frame * 4
                    body_bytes = len(payload) - 4
                    if body_bytes <= 0 or body_bytes % (floats_per_frame * 4) != 0:
                        await websocket.send_json({"error": "binary payload misaligned"})
                        continue
                    T = body_bytes // (floats_per_frame * 4)
                    if T < 5 or T > 64:
                        await websocket.send_json({"error": "frame count out of range"})
                        continue
                    arr = np.frombuffer(payload, dtype=np.float32, offset=4)
                    if arr.size != T * floats_per_frame:
                        await websocket.send_json({"error": "binary payload misaligned"})
                        continue
                    data_np = arr.reshape(T, landmarks_per_frame, 4)
                else:
                    try:
                        data_json = await asyncio.wait_for(
                            websocket.receive_json(),
                            timeout=WS_RECEIVE_TIMEOUT_MS / 1000,
                        )
                    except asyncio.TimeoutError:
                        await websocket.send_json({"error": "receive timeout"})
                        continue
                    frames = data_json.get("frames", [])
                    if len(frames) < 5:
                        await websocket.send_json({"error": "Too few frames (min 5)"})
                        continue
                    data_np = frames  # validate_frames converts and reports ragged input

                result, lstm_ms = _infer(validate_frames(data_np))
                await websocket.send_json(result)
                await asyncio.to_thread(_log_audit, "prediction", lstm_ms=round(lstm_ms, 2), confidence=result["confidence"])

                if TIMING_MODE != "off":
                    cycle_id = _timing_next_cycle_id()
                    _timing_emit_cycle({
                        "cycle_id": cycle_id,
                        "lstm_ms": round(lstm_ms, 2),
                        "total_ms": round(lstm_ms, 2),
                        "top3_count": len(result["top3"]),
                        "source": "ws_predict",
                    })
            except WebSocketDisconnect:
                raise
            except Exception as e:
                await websocket.send_json({"error": str(e)})
                continue

    except WebSocketDisconnect:
        print("[Nexora] Client disconnected from WebSocket")

@app.post("/process_sentence")
def process_sentence(payload: SentencePayload):
    t0 = time.perf_counter()
    translation_t0 = time.perf_counter()
    words = payload.words.strip()
    if not words:
        raise HTTPException(status_code=400, detail="Empty words")

    cache_key = _normalize_words(words)
    source = "template"

    # --- Step 1: Try template match (instant) ---
    natural_sentence = _match_template(words)

    # Idle-only input carries no signed content: discard (CU-02 3a2b), no LLM/TTS
    if not cache_key:
        natural_sentence = NO_CLARO
        source = "no_claro"

    # --- Step 2: Try translation cache (instant) ---
    if natural_sentence is None:
        cached = _cache_get(_translation_cache, cache_key)
        if cached is not None:
            natural_sentence = cached
            source = "cache"

    # --- Step 3: Fall back to Ollama (slow) ---
    if natural_sentence is None:
        source = "ollama"
        prompt = f"""Sos un intérprete que traduce secuencias de palabras sueltas en Lengua de Señas Argentina (LSA) a oraciones en español argentino, para uso médico (consultorio/guardia).

Reglas:
1. Armá UNA sola oración natural y gramaticalmente correcta a partir de las palabras dadas.
2. Respetá el sujeto real de las palabras: si aparece "yo" o no hay sujeto explícito, asumí primera persona ("tengo", "siento"). Si aparece "ella", "él", "vos" u otro sujeto, respetalo y conjugá acorde.
3. En español argentino evitamos "yo tengo" al inicio: usamos directamente el verbo conjugado en presente indicativo ("tengo", "siento", "duele").
4. REGLA CRÍTICA: ESTÁ ESTRICTAMENTE PROHIBIDO inventar, asumir o agregar síntomas, causas, enfermedades o partes del cuerpo que no estén EXPRESAMENTE mencionadas en las palabras a traducir. Limitate 100% a las palabras dadas.
5. No agregues saludos, aclaraciones, ni explicaciones. Respondé solo con la oración final.
6. Si las palabras no forman una idea clara o son insuficientes, respondé exactamente: "NO_CLARO".

Ejemplos:
Palabras a traducir: "yo dolor cabeza mucho"
Traducción: Tengo mucho dolor de cabeza.

Palabras a traducir: "ella dolor pecho"
Traducción: Ella tiene dolor en el pecho.

Palabras a traducir: "yo dolor brazo"
Traducción: Me duele el brazo.

Palabras a traducir: "idle idle"
Traducción: NO_CLARO

Palabras a traducir: "{words}"
Traducción:"""

        natural_sentence = words  # fallback
        try:
            ollama_res = requests.post(
                "http://127.0.0.1:11434/api/generate",  # not localhost: Windows tries IPv6 ::1 first and waits ~2 s before IPv4
                json={
                    "model": "qwen2:1.5b",
                    "prompt": prompt,
                    "stream": True,
                    "keep_alive": "30m",
                    "options": {"temperature": 0, "num_predict": 60},
                },
                timeout=5,
                stream=True,
            )
            if ollama_res.status_code == 200:
                tokens: list[str] = []
                for line in ollama_res.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        tokens.append(token)
                    if chunk.get("done"):
                        break
                result = "".join(tokens).strip()
                if NO_CLARO in result:
                    natural_sentence = NO_CLARO
                elif result and _is_faithful(result, words):
                    natural_sentence = result
                    _cache_put(_translation_cache, cache_key, natural_sentence, MAX_TRANSLATION_CACHE)
                else:
                    print(f"[Nexora] LLM sentence rejected by fidelity check: '{result}'")
        except Exception as e:
            print(f"[Nexora] Ollama error: {e}")

    translation_ms = (time.perf_counter() - translation_t0) * 1000.0

    # --- Step 4: TTS with audio cache ---
    tts_t0 = time.perf_counter()
    audio_base64 = ""
    if piper_voice and natural_sentence and natural_sentence != NO_CLARO:
        cached_audio = _cache_get(_audio_cache, natural_sentence)
        if cached_audio is not None:
            audio_base64 = cached_audio
        else:
            try:
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(piper_voice.config.sample_rate)
                    piper_voice.synthesize_wav(natural_sentence, wav_file)

                audio_bytes = buf.getvalue()
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                _cache_put(_audio_cache, natural_sentence, audio_base64, MAX_AUDIO_CACHE)
            except Exception as e:
                print(f"[Nexora] Piper error: {e}")
    tts_ms = (time.perf_counter() - tts_t0) * 1000.0

    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"[Nexora] process_sentence: {elapsed_ms:.0f}ms (source={source}) '{words}' -> '{natural_sentence}'")

    _log_audit(
        "sentence",
        translation_ms=round(translation_ms, 2),
        tts_ms=round(tts_ms, 2),
        total_ms=round(elapsed_ms, 2),
        source=source,
        word_count=len(words.split()),
    )

    if TIMING_MODE != "off":
        cycle_id = _timing_next_cycle_id()
        _timing_emit_cycle({
            "cycle_id": cycle_id,
            "translation_ms": round(translation_ms, 2),
            "tts_ms": round(tts_ms, 2),
            "total_ms": round(elapsed_ms, 2),
            "source": source,
        })

    return {
        "original": words,
        "natural_sentence": natural_sentence,
        "audio_base64": audio_base64,
        "source": source,
        "latency_ms": round(elapsed_ms),
    }


@app.get("/debug/timings.jsonl")
def debug_timings():
    if TIMING_MODE != "jsonl" or not TIMING_ENDPOINT_ENABLED:
        raise HTTPException(status_code=404, detail="timing disabled")
    return StreamingResponse(
        _stream_timings_tail(),
        media_type="application/x-ndjson",
    )
