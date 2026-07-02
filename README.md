# Nexora Sign Language Recognition

Este proyecto implementa un sistema end-to-end de reconocimiento de Lengua de Señas Argentina (LSA). Utiliza **MediaPipe Tasks** en el cliente web (Next.js) para extraer de forma ultra liviana los esqueletos 3D corporales y de manos directamente desde la cámara del navegador, y un backend en **FastAPI** impulsado por una red **LSTM (Long Short-Term Memory)** en PyTorch entrenada a medida.

El flujo de trabajo actual está pensado para **evitar el "domain shift"**, permitiéndote grabar tu propio dataset directamente desde la cámara web y entrenar tu propia versión del modelo LSTM para tu entorno, ángulo de visión y contextura física de forma iterativa.

## Requisitos Previos
- Python 3.9 o superior.
- Node.js (18+) y NPM.

## Configuración del Entorno

### 1. Backend (FastAPI + PyTorch)
Abrí una terminal en la raíz del proyecto y configurá Python:

```powershell
# Crear y activar entorno virtual (Windows)
python -m venv venv
.\venv\Scripts\activate

# Instalar dependencias livianas (PyTorch, FastAPI, NumPy)
pip install -r requirements.txt
```

### 2. Frontend (Next.js)
Abrí otra terminal y navegá a la carpeta `web/`:

```powershell
cd web
npm install
```

## Flujo de Trabajo: Captura, Entrenamiento e Inferencia

El proyecto opera bajo un flujo de retroalimentación continua: podés grabar datos, entrenar y predecir sobre tu entorno.

### 1. Levantar los servidores
Asegurate de tener corriendo tanto el backend como el frontend al mismo tiempo en dos consolas separadas:

**Terminal Backend (Raíz):**
```powershell
python -m uvicorn app:app --reload
```

**Terminal Frontend (`web/`):**
```powershell
npm run dev
```
Luego abrí `http://localhost:3000` en tu navegador.

### 2. Capturar tu Dataset Custom
1. En la aplicación web, activá el modo **Capturar Dataset**.
2. Seleccioná la seña que querés grabar desde el menú desplegable (ej. *Dolor*, *Doctor*, *Ayuda*, *Revisar*, *Respirar*).
3. Hacé el gesto frente a la cámara web. Cada vez que frenes la grabación, un archivo `.npy` con los esqueletos 3D se guardará automáticamente en el backend (en la ruta `dataset/custom/`).
4. Repetí hasta tener al menos **20 muestras por cada seña** para una prueba piloto decente. El contador web consultará automáticamente a la API y te mostrará en tiempo real tu progreso para cada etiqueta.

### 3. Entrenar el Modelo LSTM
Una vez que tengas suficientes datos grabados, frená o abrí otra terminal en el backend (con tu entorno virtual activado) y ejecutá el entrenamiento:

```powershell
python train_lstm.py
```

El script tomará todas tus grabaciones en `dataset/custom/`, las mezclará aleatoriamente, separará un 20% para validación y entrenará una red LSTM veloz de 2 capas. Finalizado el proceso, se generarán los archivos `models/lstm.pth` y `models/custom_classes.json`.

### 4. Predicción en Vivo
Volvé a iniciar la API de FastAPI con Uvicorn (si la habías frenado). Al arrancar, el servidor detectará automáticamente la existencia del nuevo `lstm.pth`.
Finalmente, en la aplicación web activá el modo **Inferencia**. A partir de ahora, MediaPipe extraerá tus esqueletos en vivo y el modelo te reconocerá en la pantalla.
