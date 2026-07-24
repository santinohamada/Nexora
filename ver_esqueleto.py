import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Mapa de conexiones oficiales de MediaPipe
POSE_CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20), (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32)]
HAND_CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]

if len(sys.argv) < 2:
    print("Error: Falta el archivo .npy")
    print("Uso: python ver_esqueleto.py <ruta_al_archivo.npy>")
    sys.exit(1)

filepath = sys.argv[1]
try:
    data = np.load(filepath)
except Exception as e:
    print(f"Error cargando {filepath}: {e}")
    sys.exit(1)

print(f"[+] Cargado: {filepath}")
print(f"[i] Shape del array: {data.shape}")

if len(data.shape) != 3 or data.shape[1] != 75:
    print("[!] Advertencia: El script espera shape (Frames, 75, 4) según tu código de Nexora.")
    print("Si crashea, es porque los índices no coinciden.")

# --- Setup del gráfico ---
fig, ax = plt.subplots(figsize=(6, 8))
fig.canvas.manager.set_window_title('Visualizador de MediaPipe')
ax.set_facecolor('black')
fig.patch.set_facecolor('black')

# Puntos (Scatter) y Líneas (Plot)
scatter = ax.scatter([], [], c='white', s=15, zorder=3)
lines = []

# Pre-creamos las líneas para el cuerpo (Cian), Mano Izq (Naranja) y Mano Der (Verde)
for _ in POSE_CONNECTIONS:
    lines.append(ax.plot([], [], c='cyan', lw=2, zorder=2)[0])
for _ in HAND_CONNECTIONS:
    lines.append(ax.plot([], [], c='orange', lw=2, zorder=2)[0])
for _ in HAND_CONNECTIONS:
    lines.append(ax.plot([], [], c='green', lw=2, zorder=2)[0])

# --- Límites dinámicos ---
# Extraemos min y max de X e Y para adaptar la ventana automáticamente
min_x, max_x = np.min(data[:, :, 0]), np.max(data[:, :, 0])
min_y, max_y = np.min(data[:, :, 1]), np.max(data[:, :, 1])
pad_x = (max_x - min_x) * 0.1
pad_y = (max_y - min_y) * 0.1

ax.set_xlim(min_x - pad_x, max_x + pad_x)
# Invertimos el eje Y porque en cámaras Y=0 está arriba
ax.set_ylim(max_y + pad_y, min_y - pad_y) 
ax.axis('off') # Ocultamos los ejes para que se vea más limpio

def init():
    return [scatter] + lines

def update(frame_idx):
    frame = data[frame_idx] # Extraemos un frame -> Shape (75, 4)
    x = frame[:, 0]
    y = frame[:, 1]
    
    # 1. Actualizamos los puntos
    scatter.set_offsets(np.c_[x, y])
    
    # 2. Actualizamos las líneas
    line_idx = 0
    # Pose
    for i, j in POSE_CONNECTIONS:
        lines[line_idx].set_data([x[i], x[j]], [y[i], y[j]])
        line_idx += 1
    # Mano Izquierda (Offset 33)
    for i, j in HAND_CONNECTIONS:
        lines[line_idx].set_data([x[i+33], x[j+33]], [y[i+33], y[j+33]])
        line_idx += 1
    # Mano Derecha (Offset 33 + 21 = 54)
    for i, j in HAND_CONNECTIONS:
        lines[line_idx].set_data([x[i+54], x[j+54]], [y[i+54], y[j+54]])
        line_idx += 1
        
    ax.set_title(f"Frame {frame_idx+1} / {len(data)}", color='white')
    return [scatter] + lines

# Animamos a 30 FPS
ani = animation.FuncAnimation(
    fig, update, frames=len(data), 
    init_func=init, blit=True, interval=1000/30
)

plt.show()
