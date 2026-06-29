# Nexora Sign Language Recognition

Este proyecto utiliza **MediaPipe Holistic** para la extracción de esqueletos corporales/manos y una arquitectura **CTR-GCN** (Channel-Topology Routing Graph Convolutional Network) para el reconocimiento de la Lengua de Señas Argentina (LSA-64).

## Requisitos Previos
- Python 3.9 o superior.
- Dataset de LSA-64 (los 3.200 videos en formato `.mp4`).

## Pasos para la instalación y ejecución

### 1. Clonar el repositorio y configurar el entorno
Una vez que clones este repositorio en tu nueva máquina, abrí una terminal en la carpeta del proyecto y ejecutá:

```powershell
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar el entorno virtual (Windows)
.\venv\Scripts\activate

# 3. Instalar las dependencias
pip install -r requirements.txt
```

### 2. Preparar los datos (Dataset LSA-64)
El repositorio ignora los videos pesados para no colapsar Git. Tenés que volver a acomodarlos.
1. Creá la carpeta `data/raw_flat` y pegá adentro los 3.200 videos crudos del dataset (ej: `001_001_001.mp4`).
2. Ejecutá el script de organización (esto los va a mover a la carpeta `data/raw` separados por seña en inglés):
```powershell
python organize_dataset.py
```

### 3. Extraer Keypoints (MediaPipe)
Este paso convierte los videos en archivos `.npy` con las coordenadas 3D de los esqueletos (75 nodos). Utiliza multiprocesamiento para acelerar la extracción en CPUs multi-núcleo (ideal para Ryzen 7).
```powershell
python src/data/extract_keypoints.py --input_dir data/raw --output_dir data/processed
```
*(Nota: Esto puede tardar entre 40 minutos y un par de horas dependiendo de tu CPU. Vas a escuchar los ventiladores al máximo, es normal).*

### 4. Entrenar el Modelo
Una vez finalizada la extracción, podés entrenar la CTR-GCN. El script automáticamente detecta la cantidad de clases (64) y divide los sujetos (001-008 para train, 009-010 para validación).
```powershell
python train.py
```

### 5. Predicción en Tiempo Real (Webcam o Video)
Una vez entrenado (se generará el archivo `models/ctr_gcn.pth`), podés probarlo con tu cámara web:
```powershell
python predict.py
```
O probando un video en específico:
```powershell
python predict_video.py "ruta/al/video.mp4"
```
