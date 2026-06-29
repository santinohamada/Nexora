import cv2
import mediapipe as mp
import numpy as np
import os
import argparse
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

def extract_keypoints(results):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]) if results.pose_landmarks else np.zeros((33, 4))
    lh = np.array([[res.x, res.y, res.z, 1.0] for res in results.left_hand_landmarks.landmark]) if results.left_hand_landmarks else np.zeros((21, 4))
    rh = np.array([[res.x, res.y, res.z, 1.0] for res in results.right_hand_landmarks.landmark]) if results.right_hand_landmarks else np.zeros((21, 4))
    return np.concatenate([pose, lh, rh])

def process_single_video(video_path, out_path):
    # Skip if already exists
    if os.path.exists(out_path):
        return True
        
    try:
        # Cada proceso necesita instanciar su propio modelo Holistic
        mp_holistic = mp.solutions.holistic
        with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
            cap = cv2.VideoCapture(video_path)
            frames_data = []
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False                  
                
                results = holistic.process(image)
                keypoints = extract_keypoints(results)
                frames_data.append(keypoints)
                
            cap.release()
            
            data = np.array(frames_data)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            np.save(out_path, data)
            return True
            
    except Exception as e:
        return f"Error en {os.path.basename(video_path)}: {e}"

def main(input_dir, output_dir, workers=4):
    os.makedirs(output_dir, exist_ok=True)
    
    # Listar tareas
    tasks = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.endswith('.mp4'):
                video_path = os.path.join(root, f)
                rel_path = os.path.relpath(video_path, input_dir)
                out_path = os.path.join(output_dir, rel_path.replace('.mp4', '.npy'))
                
                # Crear directorios de antemano para evitar colisiones
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                tasks.append((video_path, out_path))
                
    if not tasks:
        print(f"No se encontraron videos en {input_dir}")
        return
        
    print(f"Procesando {len(tasks)} videos usando {workers} núcleos (procesadores)...")
    
    # Procesar en paralelo
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_video, vp, op): op for vp, op in tasks}
        
        for future in tqdm(as_completed(futures), total=len(tasks)):
            res = future.result()
            if res is not True:
                print(res)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, required=True, help='Carpeta con videos MP4')
    parser.add_argument('--output_dir', type=str, required=True, help='Carpeta destino para los .npy')
    parser.add_argument('--workers', type=int, default=os.cpu_count()-1, help='Cantidad de núcleos a usar (por defecto casi todos)')
    args = parser.parse_args()
    
    # En Windows, multiprocessing necesita freeze_support pero al estar bajo if __name__ == '__main__' es suficiente.
    main(args.input_dir, args.output_dir, args.workers)
