import cv2
import numpy as np
import argparse
import time

# Conexiones básicas para el torso y brazos (MediaPipe Pose)
POSE_CONNECTIONS = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
# Las manos tienen conexiones fijas (0-1, 1-2, etc.)
HAND_CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4),
                    (0, 5), (5, 6), (6, 7), (7, 8),
                    (5, 9), (9, 10), (10, 11), (11, 12),
                    (9, 13), (13, 14), (14, 15), (15, 16),
                    (13, 17), (17, 18), (18, 19), (19, 20),
                    (0, 17)]

def draw_skeleton(frame, data_frame, width=640, height=480):
    """
    Dibuja el esqueleto 2D en una imagen a partir de los datos.
    data_frame: array de shape (75, 4) -> (x, y, z, conf)
    """
    # Escalar coordenadas relativas [0, 1] al tamaño de la pantalla
    h, w = height, width
    
    # 1. Pose (0 al 32)
    for connection in POSE_CONNECTIONS:
        p1 = data_frame[connection[0]]
        p2 = data_frame[connection[1]]
        
        # Solo dibujar si la confianza/visibilidad es > 0.5
        if p1[3] > 0.5 and p2[3] > 0.5:
            x1, y1 = int(p1[0] * w), int(p1[1] * h)
            x2, y2 = int(p2[0] * w), int(p2[1] * h)
            cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
            cv2.circle(frame, (x1, y1), 4, (0, 255, 0), -1)
            cv2.circle(frame, (x2, y2), 4, (0, 255, 0), -1)
            
    # 2. Left Hand (33 al 53)
    offset_lh = 33
    for connection in HAND_CONNECTIONS:
        idx1, idx2 = connection[0] + offset_lh, connection[1] + offset_lh
        p1, p2 = data_frame[idx1], data_frame[idx2]
        
        # Si la suma de coordenadas es > 0 (porque seteamos 0 si no hay mano)
        if p1[0] > 0 and p2[0] > 0:
            x1, y1 = int(p1[0] * w), int(p1[1] * h)
            x2, y2 = int(p2[0] * w), int(p2[1] * h)
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 255), 2) # Amarillo
            cv2.circle(frame, (x1, y1), 3, (0, 150, 255), -1)
            
    # 3. Right Hand (54 al 74)
    offset_rh = 54
    for connection in HAND_CONNECTIONS:
        idx1, idx2 = connection[0] + offset_rh, connection[1] + offset_rh
        p1, p2 = data_frame[idx1], data_frame[idx2]
        
        if p1[0] > 0 and p2[0] > 0:
            x1, y1 = int(p1[0] * w), int(p1[1] * h)
            x2, y2 = int(p2[0] * w), int(p2[1] * h)
            cv2.line(frame, (x1, y1), (x2, y2), (255, 100, 0), 2) # Azul claro
            cv2.circle(frame, (x1, y1), 3, (255, 50, 0), -1)

def main(npy_path):
    data = np.load(npy_path)
    print(f"Cargado tensor con shape: {data.shape} (Frames, Nodos, Canales)")
    
    width, height = 640, 480
    
    for i in range(data.shape[0]):
        # Crear pantalla negra
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Dibujar
        draw_skeleton(frame, data[i], width, height)
        
        cv2.imshow("Esqueleto Extraido", frame)
        # Esperar ~33ms para simular 30 fps
        if cv2.waitKey(33) & 0xFF == ord('q'):
            break
            
    cv2.destroyAllWindows()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--npy', type=str, required=True, help='Ruta al archivo .npy generado')
    args = parser.parse_args()
    
    main(args.npy)
