import cv2
import torch
import json
import numpy as np
import mediapipe as mp
import torch.nn.functional as F

from src.model.ctr_gcn import TwoStreamModel
from src.graph.mediapipe_graph import MediaPipeGraph
from src.data.extract_keypoints import extract_keypoints
from src.data.transforms import center_skeleton, get_bone_tensor, random_temporal_shift

def main():
    # 1. Load classes
    try:
        with open('models/classes.json', 'r', encoding='utf-8') as f:
            classes = json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró models/classes.json.")
        return

    num_class = len(classes)
    model_max_frames = 100
    recording_max_frames = 60 # 2 segundos a 30fps

    # 2. Load model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    graph = MediaPipeGraph()
    A = torch.tensor(graph.get_spatial_graph(), dtype=torch.float32).to(device)
    
    model = TwoStreamModel(num_class=num_class, num_point=75, in_channels=4, num_subset=A.shape[0]).to(device)
    
    try:
        model.load_state_dict(torch.load('models/ctr_gcn.pth', map_location=device))
        model.eval()
        print("Modelo cargado exitosamente.")
    except FileNotFoundError:
        print("Error: No se encontró models/ctr_gcn.pth.")
        return

    # 3. Configure Camera
    mp_holistic = mp.solutions.holistic
    # Try camera 1 first, fallback to 0
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    # State variables
    is_recording = False
    recorded_frames = []
    current_prediction = "Lista para grabar..."
    current_confidence = 0.0

    print("\n" + "="*40)
    print("Controles de la Cámara:")
    print(" - [ESPACIO]: Iniciar o Detener grabación")
    print(" - [Q]: Salir del programa")
    print(" - [M]: Activar/Desactivar modo espejo")
    print("="*40 + "\n")

    mirror_mode = False

    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            frame = cv2.resize(frame, (1024, 576))
            if mirror_mode:
                frame = cv2.flip(frame, 1)
            
            # Convert to RGB for MediaPipe
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False

            results = holistic.process(image_rgb)
            keypoints = extract_keypoints(results)

            # Draw skeleton
            mp.solutions.drawing_utils.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)
            mp.solutions.drawing_utils.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            mp.solutions.drawing_utils.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)

            # Logic for recording
            if is_recording:
                recorded_frames.append(keypoints)
                cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1)
                cv2.putText(frame, f"GRABANDO [{len(recorded_frames)}/{recording_max_frames}]", (50, 35), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
                
                if len(recorded_frames) >= recording_max_frames:
                    is_recording = False # Auto stop at max capacity

            # Trigger Prediction when recording stops
            if not is_recording and len(recorded_frames) > 0:
                input_data = np.array(recorded_frames, dtype=np.float32)
                recorded_frames = [] # clear buffer
                
                # Only predict if we got a reasonable amount of frames (e.g. > 10)
                if len(input_data) > 10:
                    joint_data = center_skeleton(input_data)
                    bone_data = get_bone_tensor(joint_data)

                    joint_data = random_temporal_shift(joint_data, max_frames=model_max_frames, is_training=False)
                    bone_data = random_temporal_shift(bone_data, max_frames=model_max_frames, is_training=False)

                    joint_tensor = torch.tensor(joint_data, dtype=torch.float32).unsqueeze(0).to(device)
                    bone_tensor = torch.tensor(bone_data, dtype=torch.float32).unsqueeze(0).to(device)

                    with torch.no_grad():
                        outputs = model(joint_tensor, bone_tensor, A)
                        probs = F.softmax(outputs, dim=1)
                        confidence, predicted_idx = torch.max(probs, 1)

                        current_prediction = classes[predicted_idx.item()]
                        current_confidence = confidence.item() * 100
                else:
                    current_prediction = "Muy corto"
                    current_confidence = 0.0

            # HUD
            if not is_recording:
                cv2.rectangle(frame, (0, 0), (640, 100), (0, 0, 0), -1)
                cv2.putText(frame, "Mantene o presiona [ESPACIO] para grabar la sena", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
                
                color = (0, 255, 0) if current_confidence > 30 else (0, 165, 255)
                if current_confidence == 0: color = (255, 255, 255)
                
                text = f"{current_prediction} ({current_confidence:.1f}%)" if current_confidence > 0 else current_prediction
                cv2.putText(frame, text, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)
                
                mirror_text = "Modo Espejo: Activado" if mirror_mode else "Modo Espejo: Desactivado"
                cv2.putText(frame, mirror_text + " (M para cambiar)", (10, 90), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

            cv2.imshow('Nexora IA - Reconocimiento LSA', frame)

            key = cv2.waitKey(10) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('m'):
                mirror_mode = not mirror_mode
            elif key == ord(' '):
                # Start recording if not recording, stop if already recording
                is_recording = not is_recording
                if is_recording:
                    recorded_frames = [] # Start fresh
                    current_prediction = "Pensando..."
                    current_confidence = 0.0

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
