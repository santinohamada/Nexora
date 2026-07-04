import os
import json
import torch
import numpy as np
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from src.model.lstm import SignLanguageLSTM

# Configurations
DATASET_PATH = "dataset/custom"
MODELS_DIR = "models"
MODEL_PATH = os.path.join(MODELS_DIR, "lstm.pth")
CLASSES_PATH = os.path.join(MODELS_DIR, "custom_classes.json")
MAX_FRAMES = 45
BATCH_SIZE = 8
EPOCHS = 50
LEARNING_RATE = 0.001

class CustomSignDataset(Dataset):
    def __init__(self, file_paths, labels, class_to_idx, augment=False):
        self.file_paths = file_paths
        self.labels = labels
        self.class_to_idx = class_to_idx
        self.augment = augment

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        file_path = self.file_paths[idx]
        label_str = self.labels[idx]
        label_idx = self.class_to_idx[label_str]
        
        # Load numpy array: expected shape (T, 75, 4)
        data = np.load(file_path)
        
        T = data.shape[0]
        if self.augment:
            if T > MAX_FRAMES:
                start_idx = np.random.randint(0, T - MAX_FRAMES + 1)
                data = data[start_idx:start_idx + MAX_FRAMES]
            elif T < MAX_FRAMES:
                pad_len = MAX_FRAMES - T
                pad_arr = np.zeros((pad_len, 75, 4), dtype=data.dtype)
                data = np.concatenate((data, pad_arr), axis=0)
                
            noise = np.random.normal(0, 0.01, size=(MAX_FRAMES, 75, 2))
            scale = np.random.uniform(0.95, 1.05)
            data[:, :, :2] = (data[:, :, :2] * scale) + noise
        else:
            if T > MAX_FRAMES:
                data = data[:MAX_FRAMES]
            elif T < MAX_FRAMES:
                pad_len = MAX_FRAMES - T
                pad_arr = np.zeros((pad_len, 75, 4), dtype=data.dtype)
                data = np.concatenate((data, pad_arr), axis=0)
            
        # Flatten the features per frame: (MAX_FRAMES, 300)
        data = data.reshape(MAX_FRAMES, -1)
        
        return torch.tensor(data, dtype=torch.float32), torch.tensor(label_idx, dtype=torch.long)


def train():
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset path {DATASET_PATH} not found. Por favor graba algunos datos primero.")
        return

    # 1. Discover classes and gather files
    classes = sorted([d for d in os.listdir(DATASET_PATH) if os.path.isdir(os.path.join(DATASET_PATH, d))])
    
    if not classes:
        print("No se encontraron clases en el dataset. Por favor graba algunos datos primero.")
        return

    print(f"Clases encontradas: {classes}")
    
    # Save classes JSON so inference can use it
    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(CLASSES_PATH, "w", encoding="utf-8") as f:
        json.dump(classes, f, ensure_ascii=False, indent=2)

    class_to_idx = {c: i for i, c in enumerate(classes)}
    
    file_paths = []
    labels = []
    
    for c in classes:
        c_dir = os.path.join(DATASET_PATH, c)
        for f in os.listdir(c_dir):
            if f.endswith('.npy'):
                file_paths.append(os.path.join(c_dir, f))
                labels.append(c)
                
    if len(file_paths) == 0:
        print("No se encontraron archivos .npy en el dataset.")
        return
        
    print(f"Total samples: {len(file_paths)}")
    
    # Manual split train/val to avoid sklearn dependency
    import random
    combined = list(zip(file_paths, labels))
    random.seed(42)
    random.shuffle(combined)
    
    split_idx = int(len(combined) * 0.8)
    train_data = combined[:split_idx]
    val_data = combined[split_idx:]
    
    X_train = [x[0] for x in train_data]
    y_train = [x[1] for x in train_data]
    X_val = [x[0] for x in val_data]
    y_val = [x[1] for x in val_data]
    
    train_dataset = CustomSignDataset(X_train, y_train, class_to_idx, augment=True)
    val_dataset = CustomSignDataset(X_val, y_val, class_to_idx, augment=False)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # 2. Setup model, loss, optimizer
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SignLanguageLSTM(num_classes=len(classes)).to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    # 3. Training loop
    best_val_acc = 0.0
    
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        correct = 0
        total = 0
        
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
            
        train_loss = train_loss / total
        train_acc = 100. * correct / total
        
        # Validation
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                val_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
                
        val_loss = val_loss / total if total > 0 else 0
        val_acc = 100. * correct / total if total > 0 else 0
        
        print(f"Epoch {epoch+1}/{EPOCHS} | Train Loss: {train_loss:.4f} Acc: {train_acc:.2f}% | Val Loss: {val_loss:.4f} Acc: {val_acc:.2f}%")
        
        if val_acc >= best_val_acc and total > 0:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODEL_PATH)
            
    if total == 0:
        # If val size is 0 due to tiny dataset
        torch.save(model.state_dict(), MODEL_PATH)
            
    print(f"Training complete. Best val acc: {best_val_acc:.2f}%. Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train()
