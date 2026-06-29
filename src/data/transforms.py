import numpy as np
import torch

def center_skeleton(data):
    """
    Centra el esqueleto restando la posición de la nariz (nodo 0) a todos los demás nodos.
    data shape esperado: (Frames, Nodos, Canales) -> (T, 75, 4) numpy array.
    """
    centered = data.copy()
    
    # El nodo 0 es la nariz. Extraer (x, y, z)
    # Forma de nose_pos: (Frames, 1, 3)
    nose_pos = data[:, 0:1, :3]
    
    # Restar a todos los nodos (T, 75, 3) - (T, 1, 3) usa broadcasting
    centered[:, :, :3] = data[:, :, :3] - nose_pos
    
    return centered

def flip_skeleton_tensor(inputs):
    """
    inputs shape esperado: (Batch, Frames, Nodos, Canales) -> (N, T, 75, 4) tensor.
    Invierte el eje X (espejo) e intercambia los índices de la mano derecha e izquierda.
    """
    flipped = inputs.clone()
    
    # Invertir X (como ya está centrado en 0, multiplicar por -1 hace el espejo perfecto)
    flipped[:, :, :, 0] = -flipped[:, :, :, 0]
    
    # Índices para MediaPipe (intercambiar izquierdo con derecho)
    # Pose:
    left_pose = [1, 2, 3, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31]
    right_pose = [4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32]
    
    # Manos: (33 a 53 es LH, 54 a 74 es RH)
    left_hand = list(range(33, 54))
    right_hand = list(range(54, 75))
    
    all_left = left_pose + left_hand
    all_right = right_pose + right_hand
    
    # Swap 
    temp = flipped[:, :, all_left, :].clone()
    flipped[:, :, all_left, :] = flipped[:, :, all_right, :]
    flipped[:, :, all_right, :] = temp
    
    return flipped

def add_jitter_tensor(inputs, noise_level=0.01):
    """
    Agrega ruido gaussiano a las coordenadas (x,y,z) simulando temblor o mala calidad de cámara.
    inputs: tensor (N, T, 75, 4)
    """
    noisy = inputs.clone()
    noise = torch.randn_like(noisy[:, :, :, :3]) * noise_level
    noisy[:, :, :, :3] += noise
    return noisy

def get_bone_tensor(data):
    """
    Calcula el tensor de huesos (Bone) a partir del tensor de articulaciones (Joint).
    Un hueso es el vector direccional entre dos articulaciones conectadas.
    """
    from src.graph.mediapipe_graph import MediaPipeGraph
    graph = MediaPipeGraph()
    edges = graph.edge
    
    bone_data = np.zeros_like(data)
    for v1, v2 in edges:
        # bone_data apunta desde el nodo más central (v1) hacia el extremo (v2)
        bone_data[:, v2, :3] = data[:, v2, :3] - data[:, v1, :3]
    return bone_data

def random_spatial_augmentation(data, scale_range=(0.9, 1.1), shift_range=(-0.05, 0.05)):
    """
    Escalado y traslación aleatoria 2D. 
    Ideal aplicarlo DESPUÉS de centrar.
    """
    scale = np.random.uniform(*scale_range)
    shift_x = np.random.uniform(*shift_range)
    shift_y = np.random.uniform(*shift_range)
    
    aug_data = data.copy()
    aug_data[:, :, 0] = aug_data[:, :, 0] * scale + shift_x
    aug_data[:, :, 1] = aug_data[:, :, 1] * scale + shift_y
    aug_data[:, :, 2] = aug_data[:, :, 2] * scale # Z scaling
    
    return aug_data

def random_temporal_shift(data, max_frames=100, is_training=True):
    """
    Ubica la secuencia de frames en una posición temporal aleatoria dentro del tensor de max_frames.
    Si is_training=False, la centra (comportamiento determinista para inferencia/validación).
    Si los frames superan max_frames, hace random crop en training o center crop en inferencia.
    """
    num_frames = data.shape[0]
    tensor = np.zeros((max_frames, data.shape[1], data.shape[2]), dtype=np.float32)
    
    if num_frames == 0:
        return tensor
        
    if num_frames <= max_frames:
        if is_training:
            shift = np.random.randint(0, max_frames - num_frames + 1)
        else:
            shift = (max_frames - num_frames) // 2
        tensor[shift:shift+num_frames, :, :] = data
    else:
        if is_training:
            start = np.random.randint(0, num_frames - max_frames + 1)
        else:
            start = (num_frames - max_frames) // 2
        tensor = data[start:start+max_frames, :, :]
        
    return tensor
