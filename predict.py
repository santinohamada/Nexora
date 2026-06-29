import cv2
import torch
import json
import numpy as np
import mediapipe as mp
from collections import deque
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
        print("Error: No se encontró models/classes.json. Entrená el modelo primero.")
        return

    num_class = len(classes)
    num_point = 75
    in_channels = 4
    max_frames = 100
    prediction_stride = 10       # Predict every N frames once buffer is full
    smoothing_window = 5         # Average logits over last N predictions

    # 2. Load model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    graph = MediaPipeGraph()
    A = torch.tensor(graph.get_spatial_graph(), dtype=torch.float32).to(device)
    num_subset = A.shape[0]

    model = TwoStreamModel(num_class=num_class, num_point=num_point,
                           in_channels=in_channels, num_subset=num_subset).to(device)

    try:
        model.load_state_dict(torch.load('models/ctr_gcn.pth', map_location=device))
        model.eval()
        print("Modelo cargado exitosamente.")
    except FileNotFoundError:
        print("Error: No se encontró models/ctr_gcn.pth. Entrená el modelo primero.")
        return

    # 3. Configure MediaPipe and Camera
    mp_holistic = mp.solutions.holistic
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    # Rolling buffer for the last max_frames
    frames_buffer = deque(maxlen=max_frames)

    # Temporal smoothing: keep recent logits to average
    logits_history = deque(maxlen=smoothing_window)

    current_prediction = "Ninguna"
    current_confidence = 0.0
    frame_count = 0

    print("Presioná 'q' en la ventana de video para salir.")
    print(f"Stride: predicción cada {prediction_stride} frames (~{prediction_stride/30:.1f}s a 30fps)")

    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (1024, 576))
            frame_count += 1

            # Convert to RGB for MediaPipe
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False

            # MediaPipe inference
            results = holistic.process(image_rgb)

            # Extract 75 keypoints
            keypoints = extract_keypoints(results)
            frames_buffer.append(keypoints)

            # Draw skeleton
            mp.solutions.drawing_utils.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)
            mp.solutions.drawing_utils.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            mp.solutions.drawing_utils.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)

            # 4. CTR-GCN Inference with sliding window
            if len(frames_buffer) == max_frames and frame_count % prediction_stride == 0:
                input_data = np.array(frames_buffer, dtype=np.float32)

                # Spatial processing
                joint_data = center_skeleton(input_data)
                bone_data = get_bone_tensor(joint_data)

                # Temporal processing (deterministic for inference)
                joint_data = random_temporal_shift(joint_data, max_frames=max_frames, is_training=False)
                bone_data = random_temporal_shift(bone_data, max_frames=max_frames, is_training=False)

                # Add batch dimension
                joint_tensor = torch.tensor(joint_data, dtype=torch.float32).unsqueeze(0).to(device)
                bone_tensor = torch.tensor(bone_data, dtype=torch.float32).unsqueeze(0).to(device)

                with torch.no_grad():
                    outputs = model(joint_tensor, bone_tensor, A)
                    logits_history.append(outputs.cpu())

                    # Temporal smoothing: average logits over recent predictions
                    if len(logits_history) > 0:
                        avg_logits = torch.stack(list(logits_history)).mean(dim=0)
                        probs = F.softmax(avg_logits, dim=1)
                        confidence, predicted_idx = torch.max(probs, 1)

                        if confidence.item() > 0.6:
                            current_prediction = classes[predicted_idx.item()]
                            current_confidence = confidence.item() * 100
                        else:
                            current_prediction = "Dudoso..."
                            current_confidence = confidence.item() * 100

            # 5. Show HUD
            cv2.rectangle(frame, (0, 0), (640, 40), (0, 0, 0), -1)
            cv2.putText(frame, f"Prediccion: {current_prediction} ({current_confidence:.1f}%)",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, f"Frames en buffer: {len(frames_buffer)}/100",
                        (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

            cv2.imshow('Nexora IA - Reconocimiento LSA', frame)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
