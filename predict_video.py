import cv2
import torch
import json
import numpy as np
import mediapipe as mp
import argparse
import torch.nn.functional as F

from src.model.ctr_gcn import TwoStreamModel
from src.graph.mediapipe_graph import MediaPipeGraph
from src.data.extract_keypoints import process_video
from src.data.transforms import center_skeleton, get_bone_tensor, random_temporal_shift

def main(video_path):
    # 1. Cargar clases
    try:
        with open('models/classes.json', 'r', encoding='utf-8') as f:
            classes = json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró models/classes.json.")
        return

    num_class = len(classes)
    num_point = 75
    in_channels = 4
    max_frames = 100
    
    # 2. Cargar modelo
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    graph = MediaPipeGraph()
    A = torch.tensor(graph.get_spatial_graph(), dtype=torch.float32).to(device)
    num_subset = A.shape[0]
    
    model = TwoStreamModel(num_class=num_class, num_point=num_point, in_channels=in_channels, num_subset=num_subset).to(device)
    
    try:
        model.load_state_dict(torch.load('models/ctr_gcn.pth', map_location=device))
        model.eval()
    except FileNotFoundError:
        print("Error: No se encontró models/ctr_gcn.pth.")
        return

    
    # 4. Extraer Keypoints del video
    print(f"Analizando video: {video_path}...")
    mp_holistic = mp.solutions.holistic
    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        try:
            data = process_video(video_path, holistic)
        except Exception as e:
            print(f"Error procesando video: {e}")
            return
            
    if len(data) == 0:
        print("No se encontraron frames válidos en el video.")
        return
        
    # [NUEVO V3] Procesamiento Espacial
    joint_data = center_skeleton(data)
    bone_data = get_bone_tensor(joint_data)

    # [NUEVO V3] Procesamiento Temporal (Alineación/Padding centralizado)
    joint_data = random_temporal_shift(joint_data, max_frames=max_frames, is_training=False)
    bone_data = random_temporal_shift(bone_data, max_frames=max_frames, is_training=False)
        
    # 6. Inferencia
    joint_tensor = torch.tensor(joint_data, dtype=torch.float32).unsqueeze(0).to(device)
    bone_tensor = torch.tensor(bone_data, dtype=torch.float32).unsqueeze(0).to(device)
    
    with torch.no_grad():
        outputs = model(joint_tensor, bone_tensor, A)
        probs = F.softmax(outputs, dim=1)
        confidence, predicted_idx = torch.max(probs, 1)
        
        predicted_class = classes[predicted_idx.item()]
        conf_percent = confidence.item() * 100
        
    print("\n" + "="*40)
    print(" RESULTADO DE LA IA")
    print("="*40)
    print(f" -> Predicción: {predicted_class}")
    print(f" -> Seguridad:  {conf_percent:.2f}%")
    print("="*40 + "\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', type=str, required=True, help='Ruta al video .mp4 a analizar')
    args = parser.parse_args()
    
    main(args.video)
