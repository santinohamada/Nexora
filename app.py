import os
import time
import json
import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.model.ctr_gcn import TwoStreamModel
from src.model.lstm import SignLanguageLSTM
from src.graph.mediapipe_graph import MediaPipeGraph
from src.data.transforms import center_skeleton, get_bone_tensor, random_temporal_shift

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
GCN_MODEL_PATH = "models/ctr_gcn.pth"
GCN_CLASSES_PATH = "models/classes.json"

USE_LSTM = os.path.exists(LSTM_MODEL_PATH) and os.path.exists(LSTM_CLASSES_PATH)

if USE_LSTM:
    with open(LSTM_CLASSES_PATH, "r", encoding="utf-8") as f:
        CLASSES: list[str] = json.load(f)
        
    model = SignLanguageLSTM(num_classes=len(CLASSES)).to(device)
    model.load_state_dict(torch.load(LSTM_MODEL_PATH, map_location=device, weights_only=False))
    model.eval()
    MAX_FRAMES = 60
    print(f"[Nexora] Custom LSTM Model loaded on {device} — {len(CLASSES)} classes")
else:
    with open(GCN_CLASSES_PATH, "r", encoding="utf-8") as f:
        CLASSES: list[str] = json.load(f)

    graph = MediaPipeGraph()
    A = torch.tensor(graph.get_spatial_graph(), dtype=torch.float32).to(device)

    model = TwoStreamModel(
        num_class=len(CLASSES),
        num_point=75,
        in_channels=4,
        num_subset=A.shape[0],
    ).to(device)

    model.load_state_dict(
        torch.load(GCN_MODEL_PATH, map_location=device, weights_only=False)
    )
    model.eval()
    MAX_FRAMES = 100
    print(f"[Nexora] CTR-GCN Model loaded on {device} — {len(CLASSES)} classes")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class SkeletonPayload(BaseModel):
    # List of frames; each frame is a list of 75 landmarks [x, y, z, visibility]
    frames: list[list[list[float]]]

class CapturePayload(BaseModel):
    label: str
    frames: list[list[list[float]]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
os.makedirs("dataset/custom", exist_ok=True)
@app.get("/")
def health():
    return {"status": "ok", "device": str(device), "classes": len(CLASSES)}


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

    if USE_LSTM:
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
    else:
        # Same preprocessing as training for GCN
        joint_data = center_skeleton(data)
        bone_data = get_bone_tensor(joint_data)

        joint_data = random_temporal_shift(joint_data, max_frames=MAX_FRAMES, is_training=False)
        bone_data = random_temporal_shift(bone_data, max_frames=MAX_FRAMES, is_training=False)

        joint_tensor = torch.tensor(joint_data, dtype=torch.float32).unsqueeze(0).to(device)
        bone_tensor = torch.tensor(bone_data, dtype=torch.float32).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(joint_tensor, bone_tensor, A)
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
