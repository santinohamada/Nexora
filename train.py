import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
import os
import random
import math
import json

from src.model.ctr_gcn import TwoStreamModel
from src.graph.mediapipe_graph import MediaPipeGraph
from src.data.dataset import LSADataset
from src.data.transforms import flip_skeleton_tensor, add_jitter_tensor


def get_warmup_cosine_scheduler(optimizer, warmup_epochs, total_epochs, steps_per_epoch):
    """Linear warmup for warmup_epochs, then cosine annealing to 0."""
    warmup_steps = warmup_epochs * steps_per_epoch
    total_steps = total_epochs * steps_per_epoch

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    return optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def mixup_data(joint_x, bone_x, y, alpha=0.2):
    """Applies mixup augmentation to a batch."""
    if alpha > 0:
        lam = torch.distributions.Beta(alpha, alpha).sample().item()
    else:
        lam = 1.0

    batch_size = joint_x.size(0)
    index = torch.randperm(batch_size, device=joint_x.device)

    mixed_joint = lam * joint_x + (1 - lam) * joint_x[index]
    mixed_bone = lam * bone_x + (1 - lam) * bone_x[index]
    y_a, y_b = y, y[index]

    return mixed_joint, mixed_bone, y_a, y_b, lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    """Computes mixup loss as weighted sum of losses for both label sets."""
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


def train():
    # Hyperparameters
    num_point = 75
    in_channels = 4
    batch_size = 16
    epochs = 150
    learning_rate = 0.001
    warmup_epochs = 10
    mixup_alpha = 0.2

    # Cross-subject split configuration
    # LSA-64: 10 subjects (001-010). Subjects 009, 010 → validation.
    val_subjects = {'009', '010'}

    # Dataset
    data_dir = 'data/processed'
    if not os.path.exists(data_dir) or len(os.listdir(data_dir)) == 0:
        print(f"Error: La carpeta {data_dir} está vacía. Extraé los keypoints primero.")
        return

    # Create two dataset instances: one for train (with augmentation), one for val (without)
    train_dataset = LSADataset(data_dir=data_dir, max_frames=100, is_training=True)
    val_dataset = LSADataset(data_dir=data_dir, max_frames=100, is_training=False)

    # Dynamic hyperparameters
    num_class = len(train_dataset.classes)

    # Cross-subject split
    all_subjects = sorted(set(train_dataset.subject_ids))
    train_subjects = set(all_subjects) - val_subjects

    train_indices = train_dataset.get_indices_by_subjects(train_subjects)
    val_indices = val_dataset.get_indices_by_subjects(val_subjects)

    print(f"\nCross-Subject Split:")
    print(f"  Train subjects: {sorted(train_subjects)} → {len(train_indices)} videos")
    print(f"  Val subjects:   {sorted(val_subjects)} → {len(val_indices)} videos")

    if len(train_indices) == 0 or len(val_indices) == 0:
        print("Error: Split produced empty train or val set. Check subject IDs.")
        return

    train_subset = Subset(train_dataset, train_indices)
    val_subset = Subset(val_dataset, val_indices)

    train_batch = min(batch_size, len(train_indices))
    val_batch = min(batch_size, len(val_indices))

    train_loader = DataLoader(train_subset, batch_size=train_batch, shuffle=True,
                              drop_last=(len(train_indices) >= batch_size))
    val_loader = DataLoader(val_subset, batch_size=val_batch, shuffle=False)

    # Device & Graph
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nEntrenando en: {device}")

    graph = MediaPipeGraph()
    A = graph.get_spatial_graph()
    A_tensor = torch.tensor(A, dtype=torch.float32).to(device)

    # Model
    num_subset = A_tensor.shape[0]  # K=3
    model = TwoStreamModel(num_class=num_class, num_point=num_point,
                           in_channels=in_channels, num_subset=num_subset).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model: {trainable_params:,} trainable params ({total_params:,} total)\n")

    # Loss with label smoothing
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-2)

    # Warmup + Cosine Annealing scheduler
    steps_per_epoch = len(train_loader)
    scheduler = get_warmup_cosine_scheduler(optimizer, warmup_epochs, epochs, steps_per_epoch)

    # Early Stopping
    patience = 30
    best_val_loss = float('inf')
    best_val_acc = 0.0
    epochs_no_improve = 0

    # Training loop
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        correct = 0
        total = 0

        for joint_inputs, bone_inputs, labels in train_loader:
            joint_inputs = joint_inputs.to(device)
            bone_inputs = bone_inputs.to(device)
            labels = labels.to(device)

            # Data Augmentation: Flip
            if random.random() < 0.5:
                joint_inputs = flip_skeleton_tensor(joint_inputs)
                bone_inputs = flip_skeleton_tensor(bone_inputs)

            # Data Augmentation: Jitter
            joint_inputs = add_jitter_tensor(joint_inputs, noise_level=0.01)
            bone_inputs = add_jitter_tensor(bone_inputs, noise_level=0.01)

            # Mixup
            mixed_joint, mixed_bone, y_a, y_b, lam = mixup_data(
                joint_inputs, bone_inputs, labels, alpha=mixup_alpha
            )

            optimizer.zero_grad()
            outputs = model(mixed_joint, mixed_bone, A_tensor)
            loss = mixup_criterion(criterion, outputs, y_a, y_b, lam)

            loss.backward()
            optimizer.step()
            scheduler.step()

            train_loss += loss.item()
            # Track accuracy using the dominant label (lam > 0.5)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(y_a if lam >= 0.5 else y_b).sum().item()

        train_acc = 100. * correct / total if total > 0 else 0

        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for joint_inputs, bone_inputs, labels in val_loader:
                joint_inputs = joint_inputs.to(device)
                bone_inputs = bone_inputs.to(device)
                labels = labels.to(device)

                outputs = model(joint_inputs, bone_inputs, A_tensor)
                loss = nn.functional.cross_entropy(outputs, labels)  # No smoothing for val

                val_loss += loss.item()
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

        val_acc = 100. * val_correct / val_total if val_total > 0 else 0
        avg_val_loss = val_loss / len(val_loader)
        current_lr = optimizer.param_groups[0]['lr']

        print(f"Epoch [{epoch+1}/{epochs}] | "
              f"Train Loss: {train_loss/len(train_loader):.4f} - Acc: {train_acc:.2f}% | "
              f"Val Loss: {avg_val_loss:.4f} - Acc: {val_acc:.2f}% | "
              f"LR: {current_lr:.6f}")

        # Early Stopping & Model Checkpointing (by val accuracy for classification)
        if val_acc > best_val_acc or (val_acc == best_val_acc and avg_val_loss < best_val_loss):
            best_val_loss = avg_val_loss
            best_val_acc = val_acc
            epochs_no_improve = 0
            os.makedirs('models', exist_ok=True)
            torch.save(model.state_dict(), 'models/ctr_gcn.pth')
            print(f"  [*] Best model saved (Val Acc: {val_acc:.2f}%)")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"Early stopping activado. No hubo mejora durante {patience} épocas consecutivas.")
                break

    print(f"\nEntrenamiento Finalizado. Mejor Val Acc: {best_val_acc:.2f}%")

    # Save classes
    classes_path = 'models/classes.json'
    with open(classes_path, 'w', encoding='utf-8') as f:
        json.dump(train_dataset.classes, f, ensure_ascii=False, indent=4)
    print(f"Clases guardadas en {classes_path}. El modelo con mejor validación ya fue guardado en models/ctr_gcn.pth")


if __name__ == '__main__':
    train()
