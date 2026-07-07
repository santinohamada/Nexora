# Nexora: Sistema Inteligente de Comunicación y Reconocimiento de LSA

Nexora es un sistema *end-to-end* diseñado para entornos de atención médica (guardias, consultorios, recepción). Facilita la comunicación fluida entre pacientes sordos o hipoacúsicos (que utilizan Lengua de Señas Argentina - LSA) y el personal médico o de recepción.

La aplicación está diseñada con una **arquitectura de doble monitor** (o multipantalla), sincronizada en tiempo real mediante `BroadcastChannel`, e impulsada por **Inteligencia Artificial** (Visión por computadora, Modelos de Lenguaje Grandes, y Síntesis/Reconocimiento de Voz) corriendo de manera local.

---

## 🚀 Arquitectura y Componentes Principales

La interfaz se divide en un menú principal (`/`) que actúa como panel de inicio para abrir las dos estaciones de trabajo independientes:

### 1. Estación del Paciente (`/paciente`)
Pensada para la pantalla que mira hacia el paciente.
- **Captura de Señas (MediaPipe Holistic):** Extrae 33 puntos corporales y 21 de cada mano en tiempo real desde la cámara.
- **Predicción (PyTorch LSTM):** El modelo predice la seña actual a partir de una ventana de 45 frames. Si la confianza supera el 70%, registra la seña.
- **Generación de Oraciones (Ollama):** Cuando el paciente baja las manos (posición "idle") por 2 segundos, la secuencia de señas sueltas (ej: "yo dolor cabeza") se envía a un LLM local (`qwen2:1.5b`) que la transforma en una oración natural ("Tengo mucho dolor de cabeza").
- **Síntesis de Voz (Piper TTS):** La oración natural se reproduce en los parlantes usando un modelo Text-To-Speech (voz argentina).
- **Modo Captura de Datos:** Permite al usuario grabar nuevas muestras (de 45 frames) con una cuenta regresiva para nutrir el modelo personalizado de PyTorch, actualizando dinámicamente las etiquetas disponibles desde el backend.

### 2. Estación de Recepción / Enfermería (`/recepcion`)
Pensada para el monitor del personal, quien lee lo que el paciente dice y responde.
- **Historial de Chat Sincronizado:** Ve los mensajes que genera la IA del paciente al instante.
- **Panel de Respuesta:** Puede escribir con teclado.
- **Dictado Inteligente (Voice-To-Text):** Permite hacer click en el micrófono y dictar con la voz la respuesta. Utiliza la *Web Speech API* nativa del navegador para convertir voz a texto rápidamente y enviarlo al monitor del paciente.

---

## 🛠 Stack Tecnológico

**Frontend (Web)**
- Next.js 14, React, TailwindCSS, TypeScript.
- **MediaPipe Tasks** (Extracción de landmarks hiper liviana).
- **Web Speech API** (Dictado por voz nativo, sin backend).
- **BroadcastChannel API** (Sincronización de chat P2P instantánea entre pestañas, 0 latencia).

**Backend (IA & Servidor)**
- **FastAPI** + **Uvicorn** (API REST rápida y asíncrona).
- **PyTorch** (Red Neuronal LSTM entrenada a medida).
- **Ollama** (Ejecución local de modelos de lenguaje - Qwen2 1.5b).
- **Piper TTS** (Modelo ultra rápido de síntesis de voz ONNX).

---

## ⚙️ Guía de Instalación y Uso

### 1. Prerrequisitos
- **Node.js** (18+) y NPM.
- **Python** (3.9+) y Pip.
- **Ollama** instalado en el sistema.

### 2. Configurar el Backend (PyTorch + FastAPI)
1. Abrí una terminal en la raíz del proyecto.
2. Creá e iniciá tu entorno virtual:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Instalá las dependencias:
   ```powershell
   pip install -r requirements.txt
   ```
4. Asegurate de tener el modelo de voz `.onnx` descargado dentro de la carpeta `voices/` y los pesos del LSTM en `models/`.
   link: https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_AR/daniela/high

### 3. Configurar el Frontend (Next.js)
1. Abrí otra terminal y navegá a `web/`.
2. Instalá las dependencias web:
   ```powershell
   cd web
   npm install
   ```

### 4. Iniciar el Sistema (Ejecutar 3 consolas a la vez)
Para que el flujo completo funcione localmente:

- **Consola 1 (Ollama):** Mantené corriendo el cerebro lingüístico.
  ```powershell
  ollama run qwen2:1.5b
  ```
- **Consola 2 (API Backend):** En la raíz del proyecto, con el `venv` activado.
  ```powershell
  python -m uvicorn app:app --reload
  ```
- **Consola 3 (Next.js):** En la carpeta `web/`.
  ```powershell
  npm run dev
  ```

---

## 🧑‍⚕️ Cómo Operar el Sistema (Paso a Paso)

1. Abrí `http://localhost:3000` en tu navegador (preferentemente Google Chrome para mejor soporte de voz).
2. Verás el panel de **Bienvenido a Nexora**.
3. Hacé click en **Estación del Paciente** (`/paciente`). Arrastrá esta pestaña al monitor que mirará el paciente. Autorizá el uso de la cámara.
4. Volvé al menú inicial en otra pestaña y hacé click en **Estación de Recepción** (`/recepcion`). Arrastrá esta ventana a tu monitor.
5. **Comunicación:** 
   - El paciente hace señas -> El backend detecta las señas. Al bajar las manos ("idle"), Ollama forma la oración, Piper la habla en voz alta, y se envía automáticamente al chat.
   - ¡Magia! El mensaje aparece instantáneamente en el monitor de recepción gracias a la API de canales nativos.
   - El recepcionista toca el botón del micrófono, dicta su respuesta, presiona *Enviar*, y el paciente lo lee en su pantalla.

---

## 🧪 Cómo Grabar Nuevas Señas (Modo Captura)

Si necesitás enseñar palabras nuevas a la red neuronal:
1. Desde la vista de **Estación del Paciente**, hacé click en el botón gris inferior que dice **Ajustes (Modo Captura)**.
2. Seleccioná la seña que querés entrenar desde el menú desplegable (esta lista se carga dinámicamente desde `models/custom_classes.json` mediante el endpoint `/classes`).
3. Ingresá la cantidad de **Repeticiones** que deseás hacer de corrido.
4. Presioná **Empezar**. El sistema iniciará una cuenta regresiva visual enorme (3... 2... 1...) y grabará `45 frames` con la etiqueta "GRABANDO".
5. Los archivos de datos `.npy` se guardarán automáticamente en la carpeta `dataset/custom/` gracias a una petición por detrás sin trabar la interfaz.
6. Entrená el modelo de nuevo ejecutando `python train_lstm.py` cuando juntes más de 20 muestras por seña.
