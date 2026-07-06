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

### 5. Configurar la cantidad de frames
Por defecto, el proyecto captura e infiere usando ventanas de 45 frames. Si necesitás cambiar esta cantidad de frames (por ejemplo a 30 o 60), tenés que modificar 3 variables en el código de forma coordinada:

1. **Backend - Inferencia** (`app.py`): Modificá la variable `MAX_FRAMES` a la cantidad deseada.
2. **Backend - Entrenamiento** (`train_lstm.py`): Modificá la variable `MAX_FRAMES` a la cantidad deseada.
3. **Frontend - Captura** (`web/app/page.tsx`): Modificá la constante `RECORDING_MAX_FRAMES` a la cantidad deseada.

> **Importante**: Si cambiás la cantidad de frames, los archivos `.npy` de tu dataset actual dejarán de ser compatibles. Recordá renombrar la carpeta `dataset/custom/` a modo de backup y crear una nueva para poder grabar el dataset ajustado a los nuevos tiempos.

### 6. Configurar Umbral de Inferencia (Threshold)
Durante la predicción en vivo, el sistema ignorará cualquier seña que no supere un umbral de confianza mínimo para evitar falsos positivos y traducciones erróneas.
Si deseás que el modelo sea más exigente o más permisivo a la hora de escribir una palabra en el cuadro de texto de traducción, podés modificar este umbral:

1. Abrí el archivo de frontend `web/app/page.tsx`.
2. Al inicio del archivo (alrededor de la línea 9), buscá la constante:
   ```typescript
   const CONFIDENCE_THRESHOLD = 70;
3. Cambiá `70` (que representa un 70% de confianza) por el valor que prefieras (por ejemplo, `95` para ser más estricto, o `60` si tu modelo recién está aprendiendo).

### 7. Traducción Natural (LLM) y Voz (TTS)
El sistema cuenta con un pipeline inteligente de procesamiento de lenguaje natural. Cuando el usuario realiza una secuencia de señas y luego baja las manos (estado `idle` de reposo) por 2 segundos, el sistema asume que la oración terminó y se activa el proceso:

1. **Traducción (Ollama):** La secuencia de palabras sueltas (ej: "ayuda doctor rápido") se envía a un modelo de lenguaje local corriendo vía [Ollama](https://ollama.com/) (por defecto usa `qwen2:1.5b`). El LLM sigue reglas de contexto médico para transformar la secuencia en una oración fluida ("Necesito ayuda del doctor, rápido").
2. **Síntesis de Voz (Piper TTS):** Esa oración natural pasa inmediatamente por un modelo Text-To-Speech (TTS) ultra rápido y local llamado Piper (con voz argentina "Daniela"). El backend procesa el audio 100% en memoria (RAM).
3. **Reproducción Web:** El audio generado se envía en formato Base64 al cliente web de Next.js, que instancia un objeto nativo de HTML5 para reproducirlo automáticamente de forma imperceptible.

**Requisitos para esta función:**
- Instalar Ollama y mantener el modelo corriendo en una terminal de fondo: `ollama run qwen2:1.5b`
- Descargar y ubicar el modelo `.onnx` de la voz en `voices/es_AR-daniela-high.onnx`.
- (Opcional) Si preferís usar otro modelo en Ollama (ej. `llama3` o `mistral`), podés modificar el string `"model"` dentro del endpoint `/process_sentence` en `app.py`.
