import os
import time
import json
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
from piper.voice import PiperVoice
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.model.lstm import SignLanguageLSTM
from capture_validation import validate_capture_blendshapes, validate_capture_label

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Nexora LSA-64 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
LSTM_VERSIONED_MODEL_PATH = (
    "models/lstm_v2_24frames.pth"
    if LSTM_MAX_FRAMES == 24
    else f"models/lstm_v1_{LSTM_MAX_FRAMES}frames.pth"
)
LEGACY_MODEL_PATH = "models/lstm.pth"
LSTM_CLASSES_PATH = "models/custom_classes.json"

if os.path.exists(LSTM_VERSIONED_MODEL_PATH):
    LSTM_MODEL_PATH = LSTM_VERSIONED_MODEL_PATH
elif os.path.exists(LEGACY_MODEL_PATH):
    LSTM_MODEL_PATH = LEGACY_MODEL_PATH
else:
    LSTM_MODEL_PATH = ""

if not LSTM_MODEL_PATH or not os.path.exists(LSTM_CLASSES_PATH):
    print("[Nexora] ATENCIÓN: No se encontraron los archivos del modelo LSTM. Por favor graba datos y entrena el modelo.")
    CLASSES = []
    model = None
    MAX_FRAMES = LSTM_MAX_FRAMES
else:
    with open(LSTM_CLASSES_PATH, "r", encoding="utf-8") as f:
        CLASSES = json.load(f)

    model = SignLanguageLSTM(num_classes=len(CLASSES)).to(device)
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
    mode: str = "legacy"
    frames: list[list[list[float]]]
    blendshapes: list[list[float]] | None = None

class SentencePayload(BaseModel):
    words: str


def _prepare_input(data: np.ndarray) -> np.ndarray:
    T = data.shape[0]
    if T > MAX_FRAMES:
        data = data[-MAX_FRAMES:]
    elif T < MAX_FRAMES:
        pad_len = MAX_FRAMES - T
        pad_arr = np.zeros((pad_len, 75, 4), dtype=data.dtype)
        data = np.concatenate((data, pad_arr), axis=0)
    return data.reshape(MAX_FRAMES, -1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
os.makedirs("dataset/custom", exist_ok=True)
@app.get("/")
def health():
    return {"status": "ok", "device": str(device), "classes": len(CLASSES)}

@app.get("/classes")
def get_classes():
    return CLASSES


@app.get("/dataset_stats")
def dataset_stats(mode: str = "legacy"):
    stats = {}
    base_dir = os.path.join("dataset", "custom" if mode == "legacy" else "custom_tasks")
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

    mode = payload.mode if payload.mode in ("legacy", "tasks") else "legacy"
    T = len(payload.frames)

    data = np.array(payload.frames, dtype=np.float32)
    if not np.isfinite(data).all():
        raise HTTPException(status_code=400, detail="Non-finite frame value")

    try:
        blendshapes_arr = validate_capture_blendshapes(mode, T, payload.blendshapes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    timestamp = int(time.time() * 1000)
    landmarks_root = "dataset/custom" if mode == "legacy" else "dataset/custom_tasks"
    label_dir = os.path.join(landmarks_root, payload.label)
    os.makedirs(label_dir, exist_ok=True)
    filename = os.path.join(label_dir, f"{timestamp}.npy")
    np.save(filename, data)

    if mode == "tasks":
        blendshapes_dir = os.path.join("dataset", "custom_blendshapes", payload.label)
        os.makedirs(blendshapes_dir, exist_ok=True)
        blendshapes_filename = os.path.join(blendshapes_dir, f"{timestamp}.npy")
        np.save(blendshapes_filename, blendshapes_arr)

    count = len(os.listdir(label_dir))
    return {"status": "ok", "saved_to": filename, "samples_for_label": count}


@app.post("/predict")
def predict(payload: SkeletonPayload):
    if len(payload.frames) < 5:
        raise HTTPException(status_code=400, detail="Too few frames (min 5)")

    data = np.array(payload.frames, dtype=np.float32)  # (T, 75, 4)

    if model is None:
        raise HTTPException(status_code=500, detail="Modelo no entrenado. Por favor entrena el LSTM primero.")

    # LSTM Preprocessing
    data = _prepare_input(data)
    input_tensor = torch.tensor(data, dtype=torch.float32).unsqueeze(0).to(device)

    if TIMING_MODE != "off":
        lstm_t0 = time.perf_counter()

    with torch.no_grad():
        outputs = model(input_tensor)
        probs = F.softmax(outputs, dim=1)
        confidence, predicted_idx = torch.max(probs, 1)

    # Top-3 for debugging
    top3_probs, top3_idx = torch.topk(probs, 3, dim=1)
    top3 = [
        {"sign": CLASSES[i.item()], "confidence": round(p.item() * 100, 2)}
        for p, i in zip(top3_probs[0], top3_idx[0])
    ]

    if TIMING_MODE != "off":
        lstm_ms = (time.perf_counter() - lstm_t0) * 1000.0
        cycle_id = _timing_next_cycle_id()
        _timing_emit_cycle({
            "cycle_id": cycle_id,
            "lstm_ms": round(lstm_ms, 2),
            "total_ms": round(lstm_ms, 2),
            "top3_count": len(top3),
            "source": "predict",
        })

    return {
        "sign": CLASSES[predicted_idx.item()],
        "confidence": round(confidence.item() * 100, 2),
        "top3": top3,
    }

@app.websocket("/ws/predict")
async def websocket_predict(websocket: WebSocket):
    await websocket.accept()
    if model is None:
        await websocket.close(code=1011, reason="Modelo no entrenado")
        return

    proto_version = "1"
    try:
        query = getattr(websocket, "scope", {}).get("query", {})
        if isinstance(query, dict):
            proto_version = str(query.get("v", "1") or "1").lower()
    except Exception:
        proto_version = "1"

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
                    data_np = np.array(frames, dtype=np.float32)

                if data_np is None:
                    continue

                data_np = _prepare_input(data_np)
                input_tensor = torch.tensor(data_np, dtype=torch.float32).unsqueeze(0).to(device)

                if TIMING_MODE != "off":
                    lstm_t0 = time.perf_counter()

                with torch.no_grad():
                    outputs = model(input_tensor)
                    probs = F.softmax(outputs, dim=1)
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
                await websocket.send_json(result)

                if TIMING_MODE != "off":
                    lstm_ms = (time.perf_counter() - lstm_t0) * 1000.0
                    cycle_id = _timing_next_cycle_id()
                    _timing_emit_cycle({
                        "cycle_id": cycle_id,
                        "lstm_ms": round(lstm_ms, 2),
                        "total_ms": round(lstm_ms, 2),
                        "top3_count": len(top3),
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
Traducción: Me duele el brazo. (NO agregues fiebre, ni cansancio, ni nada extra).

Palabras a traducir: "idle idle"
Traducción: NO_CLARO

Palabras a traducir: "{words}"
Traducción:"""

        natural_sentence = words  # fallback
        try:
            ollama_res = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2:1.5b",
                    "prompt": prompt,
                    "stream": True
                },
                timeout=8,
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
                if result and result != "NO_CLARO":
                    natural_sentence = result
                    _cache_put(_translation_cache, cache_key, natural_sentence, MAX_TRANSLATION_CACHE)
        except Exception as e:
            print(f"[Nexora] Ollama error: {e}")

    translation_ms = (time.perf_counter() - translation_t0) * 1000.0

    # --- Step 4: TTS with audio cache ---
    tts_t0 = time.perf_counter()
    audio_base64 = ""
    if piper_voice and natural_sentence:
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
