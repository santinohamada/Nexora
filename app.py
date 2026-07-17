import os
import time
import json
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
from pydantic import BaseModel

from src.model.lstm import SignLanguageLSTM

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
# Load model once at startup
# ---------------------------------------------------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

LSTM_MODEL_PATH = "models/lstm.pth"
LSTM_CLASSES_PATH = "models/custom_classes.json"

if not os.path.exists(LSTM_MODEL_PATH) or not os.path.exists(LSTM_CLASSES_PATH):
    print("[Nexora] ATENCIÓN: No se encontraron los archivos del modelo LSTM. Por favor graba datos y entrena el modelo.")
    # Initialize empty classes and dummy model to avoid crash, but predict will fail if not trained
    CLASSES = []
    model = None
else:
    with open(LSTM_CLASSES_PATH, "r", encoding="utf-8") as f:
        CLASSES = json.load(f)
        
    model = SignLanguageLSTM(num_classes=len(CLASSES)).to(device)
    model.load_state_dict(torch.load(LSTM_MODEL_PATH, map_location=device, weights_only=False))
    model.eval()
    MAX_FRAMES = 45
    print(f"[Nexora] Custom LSTM Model loaded on {device} — {len(CLASSES)} classes")

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
}


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
    frames: list[list[list[float]]]

class SentencePayload(BaseModel):
    words: str


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
    
    label_dir = os.path.join("dataset", "custom", payload.label)
    os.makedirs(label_dir, exist_ok=True)
    
    data = np.array(payload.frames, dtype=np.float32)
    timestamp = int(time.time() * 1000)
    filename = os.path.join(label_dir, f"{timestamp}.npy")
    
    np.save(filename, data)
    
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
    T = data.shape[0]
    if T > MAX_FRAMES:
        data = data[:MAX_FRAMES]
    elif T < MAX_FRAMES:
        pad_len = MAX_FRAMES - T
        pad_arr = np.zeros((pad_len, 75, 4), dtype=data.dtype)
        data = np.concatenate((data, pad_arr), axis=0)
        
    data = data.reshape(MAX_FRAMES, -1)
    input_tensor = torch.tensor(data, dtype=torch.float32).unsqueeze(0).to(device)
    
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
        
    try:
        while True:
            # Receive frames
            data_json = await websocket.receive_json()
            frames = data_json.get("frames", [])
            if len(frames) < 5:
                await websocket.send_json({"error": "Too few frames (min 5)"})
                continue
                
            data_np = np.array(frames, dtype=np.float32)
            
            # LSTM Preprocessing
            T = data_np.shape[0]
            if T > MAX_FRAMES:
                data_np = data_np[:MAX_FRAMES]
            elif T < MAX_FRAMES:
                pad_len = MAX_FRAMES - T
                pad_arr = np.zeros((pad_len, 75, 4), dtype=data_np.dtype)
                data_np = np.concatenate((data_np, pad_arr), axis=0)
                
            data_np = data_np.reshape(MAX_FRAMES, -1)
            input_tensor = torch.tensor(data_np, dtype=torch.float32).unsqueeze(0).to(device)
            
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

    except WebSocketDisconnect:
        print("[Nexora] Client disconnected from WebSocket")
    except Exception as e:
        import traceback
        print(f"[Nexora] WebSocket error: {e}")
        traceback.print_exc()

@app.post("/process_sentence")
def process_sentence(payload: SentencePayload):
    t0 = time.perf_counter()
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

    # --- Step 4: TTS with audio cache ---
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

    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"[Nexora] process_sentence: {elapsed_ms:.0f}ms (source={source}) '{words}' -> '{natural_sentence}'")

    return {
        "original": words,
        "natural_sentence": natural_sentence,
        "audio_base64": audio_base64,
        "source": source,
        "latency_ms": round(elapsed_ms),
    }
