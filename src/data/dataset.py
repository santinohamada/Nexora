import os
import numpy as np
import torch
from torch.utils.data import Dataset
from src.data.transforms import center_skeleton, get_bone_tensor, random_temporal_shift


class LSADataset(Dataset):
    def __init__(self, data_dir, max_frames=100, is_training=True):
        """
        Args:
            data_dir (str): Directorio base donde están las carpetas por clase
            max_frames (int): Número fijo de frames.
            is_training (bool): Si es True aplica aumentos temporales aleatorios.
        """
        self.data_dir = data_dir
        self.max_frames = max_frames
        self.is_training = is_training

        # Encontrar todas las carpetas (clases) y ordenarlas alfabéticamente
        self.classes = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))])
        self.class_to_idx = {cls_name: i for i, cls_name in enumerate(self.classes)}

        self.files = []
        self.subject_ids = []

        # Buscar recursivamente todos los .npy y guardar (path, class_idx)
        for class_name in self.classes:
            class_dir = os.path.join(data_dir, class_name)
            for f in sorted(os.listdir(class_dir)):
                if f.endswith('.npy'):
                    self.files.append((os.path.join(class_dir, f), self.class_to_idx[class_name]))
                    # Extract subject ID from filename: {class}_{subject}_{rep}.npy
                    parts = f.replace('.npy', '').split('_')
                    if len(parts) >= 2:
                        self.subject_ids.append(parts[1])
                    else:
                        self.subject_ids.append('unknown')

        if len(self.files) == 0:
            print(f"ATENCIÓN: No hay archivos .npy en {data_dir}. Corré extract_keypoints.py primero.")
        else:
            unique_subjects = sorted(set(self.subject_ids))
            print(f"Dataset cargado: {len(self.files)} videos, "
                  f"{len(self.classes)} clases, "
                  f"{len(unique_subjects)} sujetos ({', '.join(unique_subjects)})")

    def __len__(self):
        return len(self.files)

    def get_subject_id(self, idx):
        """Returns the subject identifier for the sample at given index."""
        return self.subject_ids[idx]

    def get_indices_by_subjects(self, subject_ids):
        """Returns all sample indices belonging to the given subject IDs."""
        subject_set = set(subject_ids)
        return [i for i, sid in enumerate(self.subject_ids) if sid in subject_set]

    def __getitem__(self, idx):
        file_path, class_idx = self.files[idx]

        # Cargar los datos. Shape original: (Frames, 75, 4)
        data = np.load(file_path)

        # 1. Centrar el esqueleto (Espacial Base)
        data = center_skeleton(data)

        # [NEW V3] Augmentation Espacial (Scale & Shift) solo en entrenamiento
        if self.is_training:
            from src.data.transforms import random_spatial_augmentation
            if np.random.rand() < 0.5:  # 50% de probabilidad
                data = random_spatial_augmentation(data)

        # 2. Generar tensor Bone antes del padding
        bone_data = get_bone_tensor(data)

        # 3. Aplicar Padding o Crop (Temporal Shift dinámico)
        joint_tensor = random_temporal_shift(data, self.max_frames, self.is_training)
        bone_tensor = random_temporal_shift(bone_data, self.max_frames, self.is_training)

        # Convertir a tensores de PyTorch
        joint_pt = torch.tensor(joint_tensor, dtype=torch.float32)
        bone_pt = torch.tensor(bone_tensor, dtype=torch.float32)
        label_pt = torch.tensor(class_idx, dtype=torch.long)

        return joint_pt, bone_pt, label_pt
