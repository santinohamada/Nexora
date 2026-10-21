import os
import json
import argparse
import torch
import numpy as np
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from src.features import add_hand_local_features, hand_present
from src.model.lstm import SignLanguageLSTM

# Configurations
DATASET_PATH = "dataset/custom"
MODELS_DIR = "models"
MODEL_PATH = os.path.join(MODELS_DIR, "lstm.pth")
CLASSES_PATH = os.path.join(MODELS_DIR, "custom_classes.json")
MAX_FRAMES = int(os.environ.get("LSTM_MAX_FRAMES", "45"))
BATCH_SIZE = 8
EPOCHS = 50
LEARNING_RATE = 0.001


def _center_crop(arr: np.ndarray, max_frames: int) -> np.ndarray:
    T = arr.shape[0]
    if T == max_frames:
        return arr
    if T > max_frames:
        start = max(0, (T - max_frames) // 2)
        return arr[start:start + max_frames]
    pad_len = max_frames - T
    pad_arr = np.zeros((pad_len,) + arr.shape[1:], dtype=arr.dtype)
    return np.concatenate((arr, pad_arr), axis=0)


def _random_crop(arr: np.ndarray, max_frames: int, start_idx=None) -> np.ndarray:
    T = arr.shape[0]
    if T == max_frames:
        return arr
    if T > max_frames:
        if start_idx is None:
            start_idx = np.random.randint(0, T - max_frames + 1)
        return arr[start_idx:start_idx + max_frames]
    pad_len = max_frames - T
    pad_arr = np.zeros((pad_len,) + arr.shape[1:], dtype=arr.dtype)
    return np.concatenate((arr, pad_arr), axis=0)


class CustomSignDataset(Dataset):
    def __init__(self, file_paths, labels, class_to_idx, augment=False, bs_dir=None, hand_local=1):
        self.file_paths = file_paths
        self.labels = labels
        self.class_to_idx = class_to_idx
        self.augment = augment
        # Optional blendshapes dir mirroring the landmarks layout: <bs_dir>/<label>/<file>.npy
        self.bs_dir = bs_dir
        # 0 = off, 1 = hand-local features, 2 = hand-local features + deltas
        self.hand_local = hand_local

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        file_path = self.file_paths[idx]
        label_str = self.labels[idx]
        label_idx = self.class_to_idx[label_str]

        data = np.load(file_path)
        bs = np.load(os.path.join(self.bs_dir, label_str, os.path.basename(file_path))) if self.bs_dir else None

        present = hand_present(data) if self.hand_local else None  # before noise breaks the constant-point check

        if self.augment:
            start = np.random.randint(0, max(data.shape[0] - MAX_FRAMES, 0) + 1)
            data = _random_crop(data, MAX_FRAMES, start)
            if bs is not None:
                bs = _random_crop(bs, MAX_FRAMES, start)
            noise = np.random.normal(0, 0.01, size=(MAX_FRAMES, 75, 2))
            scale = np.random.uniform(0.95, 1.05)
            data[:, :, :2] = (data[:, :, :2] * scale) + noise
        else:
            data = _center_crop(data, MAX_FRAMES)
            if bs is not None:
                bs = _center_crop(bs, MAX_FRAMES)

        if self.hand_local:
            if self.augment:  # presence was computed on the full clip; crop it the same way
                present = _random_crop(present, MAX_FRAMES, start)
            else:
                present = _center_crop(present, MAX_FRAMES)
            data = add_hand_local_features(data, present, deltas=self.hand_local == 2)
        data = data.reshape(MAX_FRAMES, -1)
        if bs is not None:
            data = np.concatenate((data, bs), axis=1)

        return torch.tensor(data, dtype=torch.float32), torch.tensor(label_idx, dtype=torch.long)


def _list_samples(data_dir):
    classes = sorted(d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d)))
    files, labels = [], []
    for c in classes:
        for f in sorted(os.listdir(os.path.join(data_dir, c))):
            if f.endswith(".npy"):
                files.append(os.path.join(data_dir, c, f))
                labels.append(c)
    return classes, files, labels


def _fit(files, labels, class_to_idx, bs_dir, seed, hand_local=1):
    """Train for a fixed EPOCHS (no checkpoint selection) and return the model."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ds = CustomSignDataset(files, labels, class_to_idx, augment=True, bs_dir=bs_dir, hand_local=hand_local)
    loader = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=True)
    input_size = 300 + 84 * hand_local + (52 if bs_dir else 0)
    model = SignLanguageLSTM(num_classes=len(class_to_idx), input_size=input_size).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    for _ in range(EPOCHS):
        model.train()
        for inputs, targets in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            criterion(model(inputs), targets).backward()
            optimizer.step()
    return model


def _predict(model, files, labels, class_to_idx, bs_dir, hand_local=1):
    device = next(model.parameters()).device
    ds = CustomSignDataset(files, labels, class_to_idx, augment=False, bs_dir=bs_dir, hand_local=hand_local)
    model.eval()
    with torch.no_grad():
        return [model(ds[i][0].unsqueeze(0).to(device)).argmax(1).item() for i in range(len(ds))]


def cross_validate(data_dir, bs_dir, folds, seed, hand_local=1):
    """Stratified k-fold (same folds for the same data_dir and seed); prints accuracy and confusion."""
    classes, files, labels = _list_samples(data_dir)
    class_to_idx = {c: i for i, c in enumerate(classes)}
    rng = np.random.RandomState(seed)
    fold_of = np.zeros(len(files), dtype=int)
    for c in classes:
        idx = rng.permutation([i for i, l in enumerate(labels) if l == c])
        fold_of[idx] = np.arange(len(idx)) % folds
    n = len(classes)
    confusion = np.zeros((n, n), dtype=int)
    accs = []
    for k in range(folds):
        tr = [i for i in range(len(files)) if fold_of[i] != k]
        te = [i for i in range(len(files)) if fold_of[i] == k]
        model = _fit([files[i] for i in tr], [labels[i] for i in tr], class_to_idx, bs_dir, seed + k, hand_local)
        preds = _predict(model, [files[i] for i in te], [labels[i] for i in te], class_to_idx, bs_dir, hand_local)
        for i, p in zip(te, preds):
            confusion[class_to_idx[labels[i]], p] += 1
        accs.append(100.0 * np.mean([class_to_idx[labels[i]] == p for i, p in zip(te, preds)]))
        print(f"fold {k}: acc {accs[-1]:.2f}% (n={len(te)})")
    print(f"CV acc: {np.mean(accs):.2f} +- {np.std(accs):.2f}")
    print("recall per class:", {c: round(float(100.0 * confusion[i, i] / confusion[i].sum()), 1) for i, c in enumerate(classes)})
    print(f"confusion (rows=true, cols=pred), classes={classes}")
    print(confusion)


def train_final(data_dir, bs_dir, out_prefix, seed, hand_local=1):
    """Train on all samples. Saves models/lstm.pth + custom_classes.json, or models/<prefix>_lstm.pt for experiments."""
    if not os.path.exists(data_dir):
        print(f"Dataset path {data_dir} not found. Por favor graba algunos datos primero.")
        return
    classes, files, labels = _list_samples(data_dir)
    if not classes:
        print("No se encontraron clases en el dataset. Por favor graba algunos datos primero.")
        return
    if not files:
        print("No se encontraron archivos .npy en el dataset.")
        return
    model = _fit(files, labels, {c: i for i, c in enumerate(classes)}, bs_dir, seed, hand_local)
    os.makedirs(MODELS_DIR, exist_ok=True)
    model_path = os.path.join(MODELS_DIR, f"{out_prefix}_lstm.pt") if out_prefix else MODEL_PATH
    classes_path = os.path.join(MODELS_DIR, f"{out_prefix}_classes.json") if out_prefix else CLASSES_PATH
    torch.save(model.state_dict(), model_path)
    with open(classes_path, "w", encoding="utf-8") as f:
        json.dump(classes, f, ensure_ascii=False, indent=2)
    print(f"Trained on {len(files)} samples. Model saved to {model_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=DATASET_PATH, help="landmarks dir")
    parser.add_argument("--blendshapes", help="blendshapes dir (adds 52 features per frame; the production model does not use them)")
    parser.add_argument("--cv", type=int, help="run stratified k-fold CV with k folds instead of training")
    parser.add_argument("--out-prefix", help="experiments: save models/<prefix>_lstm.pt instead of the production model")
    parser.add_argument("--hand-local", type=int, default=1, choices=(0, 1, 2),
                        help="0 = off, 1 = add hand-local finger features (84/frame, production), 2 = also their deltas")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.cv:
        cross_validate(args.data_dir, args.blendshapes, args.cv, args.seed, args.hand_local)
    else:
        train_final(args.data_dir, args.blendshapes, args.out_prefix, args.seed, args.hand_local)
