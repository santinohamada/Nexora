# Nexora (LSA Salud)

Sistema local de traducción de Lengua de Señas Argentina (LSA) a texto y voz para la recepción de un centro de salud. El paciente hace señas frente a una cámara; el sistema las reconoce, arma una oración en español, la muestra y la reproduce en voz alta. Recepción responde por texto o dictado. Todo corre en la propia PC (sin servicios en la nube para el reconocimiento, el LLM ni la voz).

Son dos pantallas del navegador que se sincronizan entre sí:

| Pantalla | URL | Uso |
|----------|-----|-----|
| Inicio | `http://localhost:3000/` | Acceso a las dos estaciones |
| Estación del Paciente | `http://localhost:3000/paciente` | Cámara, reconocimiento de señas, chat, Modo Captura |
| Estación de Recepción | `http://localhost:3000/recepcion` | Lee lo que dice el paciente y responde por teclado o voz |

## Contenido

- [Cómo funciona](#cómo-funciona)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Ejecución](#ejecución)
- [Uso](#uso)
- [Dataset compartido (Google Drive)](#dataset-compartido-google-drive)
- [Tests](#tests)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Problemas frecuentes](#problemas-frecuentes)
- [Documentación y equipo](#documentación-y-equipo)

## Cómo funciona

```
Navegador (Chrome)                          Backend (FastAPI, :8000)
-------------------                         ------------------------
Cámara
  -> MediaPipe Tasks (pose, manos, cara)
     muestreo a 20 fps
  -> WebSocket /ws/predict  --------------> LSTM (ventana de 45 frames x 384 features)
                                            seña + confianza
  <- seña reconocida  <--------------------
  (el paciente baja las manos = clase "idle")
  -> POST /process_sentence --------------> 1. plantilla médica (instantáneo)
                                            2. caché de traducciones
                                            3. Ollama (qwen2:1.5b)
                                            -> oración + audio Piper TTS
  <- texto + audio  <----------------------
  -> BroadcastChannel -> pantalla de Recepción (texto o dictado Web Speech API)
```

- **Frontend:** Next.js (App Router), React, Tailwind, `@mediapipe/tasks-vision`. La sincronización entre pantallas usa `BroadcastChannel`, por lo que ambas deben abrirse en el mismo navegador de la misma PC.
- **Backend:** FastAPI + PyTorch (LSTM propio) + Ollama + Piper TTS. Las traducciones reportadas y los eventos de auditoría se guardan en SQLite (`data/lsa_salud.db`, no versionada).
- Si la oración coincide con una plantilla médica o con la caché, no se llama al LLM. Una secuencia solo con `idle` se descarta como "no claro".

## Requisitos

Probado en Windows 11.

| Componente | Versión / detalle |
|------------|-------------------|
| Python | 3.10 (el `venv` del proyecto usa 3.10.11) |
| Node.js | Compatible con Next.js 16. Para los tests de UI se exige >= 22.5 |
| Navegador | Google Chrome (soporte de voz y MediaPipe) |
| Ollama | Con el modelo `qwen2:1.5b` (es el que usa `app.py`) |
| Voz Piper | `voices/es_AR-daniela-high.onnx` y su `.json`. **No está versionada** (`voices/` está en `.gitignore`) |
| GPU NVIDIA | Opcional. El backend usa CUDA si `torch` la detecta; si no, CPU |

Los pesos del LSTM (`models/lstm.pth`) y las clases (`models/custom_classes.json`) sí están en el repositorio.

## Instalación

```powershell
# 1. Clonar y entrar a la raíz del repo
git clone https://github.com/santinohamada/Nexora.git
cd Nexora

# 2. Entorno virtual y dependencias de Python
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 3. Dependencias del frontend
cd web
npm install
cd ..

# 4. Modelo de lenguaje local
ollama pull qwen2:1.5b
```

**Voz Piper.** Descargar `es_AR-daniela-high.onnx` y `es_AR-daniela-high.onnx.json` desde
<https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_AR/daniela/high> y dejarlos en `voices/` (crear la carpeta). Sin la voz el backend arranca igual, pero no genera audio.

**Archivos de MediaPipe.** `npm run dev` y `npm run build` ejecutan antes `web/scripts/fetch-mediapipe-assets.mjs`, que descarga los modelos `.task` (verifica SHA-256) y copia los `wasm` a `web/public/`. Requiere internet la primera vez.

**Configuración local (opcional).** Copiar `.env.example` a `.env` en la raíz (el `.env` no se versiona). Las variables que reconoce el backend:

| Variable | Efecto | Por defecto |
|----------|--------|-------------|
| `NEXORA_DATASET_DIR` | Carpeta del dataset (contiene `custom/` y `custom_blendshapes/`) | `dataset` |
| `NEXORA_RECORDER` | Nombre de quien graba, se agrega al nombre de cada muestra | vacío |
| `NEXORA_ALLOWED_ORIGINS` | Orígenes CORS permitidos, separados por comas | `http://localhost:3000,http://127.0.0.1:3000` |
| `NEXORA_DB_PATH` | Ruta de la base SQLite | `data/lsa_salud.db` |
| `LSTM_MAX_FRAMES` | Largo de la ventana del LSTM | `45` |
| `LATENCY_V2_TIMING` | Telemetría por etapa: `off`, `stdout` o `jsonl` | `off` |

Una variable ya definida en la consola tiene prioridad sobre el `.env`. El frontend acepta, también opcionales, `NEXT_PUBLIC_API_URL` y `NEXT_PUBLIC_WS_URL` (por defecto `http://localhost:8000` y `ws://localhost:8000`) y `NEXT_PUBLIC_MIN_SAMPLE_FPS` (ver [Modo Captura](#modo-captura)); se definen en `web/.env.local`.

## Ejecución

### Docker Compose (recomendado)

Requiere [Docker Desktop](https://www.docker.com/products/docker-desktop/) (o Docker Engine + Compose). El puerto **3000** del host debe estar libre (detené `npm run dev` si lo tenías corriendo). El API no se publica en el 8000: el navegador entra solo por el proxy en el 3000, así no choca con otros servicios que usen ese puerto.

Opcional: en `.env` de la raíz, `NEXORA_DATASET_DIR` y `NEXORA_RECORDER` (igual que en [Dataset compartido](#dataset-compartido-google-drive)); Compose monta esa carpeta en el contenedor del API.

```powershell
docker compose up --build
```

Abrí `http://localhost:3000`. La primera vez descarga dependencias de las imágenes, los modelos de MediaPipe (build del frontend), la voz Piper y el modelo `qwen2:1.5b` de Ollama; puede tardar varios minutos. Todo corre en CPU. Para entrenar el LSTM (`train_lstm.py`) seguí usando el venv en el host.

### Manual (tres terminales)

Tres procesos, cada uno en su terminal.

```powershell
# Terminal 1: Ollama (omitir si ya corre como servicio en :11434)
ollama serve

# Terminal 2: backend, SIEMPRE desde la raíz del repo y con el venv activado
.\venv\Scripts\activate
python -m uvicorn app:app --port 8000

# Terminal 3: frontend
cd web
npm run dev
```

Verificación rápida: `http://127.0.0.1:8000/` devuelve `{"status":"ok","device":...,"classes":...}` y `http://localhost:3000` muestra el inicio.

> El backend solo acepta pedidos desde los orígenes de `NEXORA_ALLOWED_ORIGINS`. Si abrís el frontend desde otra dirección (por ejemplo, la IP de la red local), agregala a esa variable.

## Uso

### Flujo normal

1. Abrir `http://localhost:3000/paciente` en Chrome y moverla al monitor del paciente.
2. Aceptar el **consentimiento** de uso de la cámara. Si se rechaza, la estación no se activa; la decisión queda registrada como evento de auditoría. Luego autorizar la cámara en el navegador.
3. Abrir `http://localhost:3000/recepcion` en otra pestaña del **mismo navegador** y moverla al monitor del personal.
4. El paciente hace las señas. Al **bajar las manos** (clase `idle`) se cierra la oración: el backend la arma (plantilla o LLM), la muestra en ambas pantallas y la reproduce con Piper.
5. Recepción responde escribiendo o con el micrófono (dictado por Web Speech API) y envía el mensaje; el paciente lo lee en su pantalla.
6. Si una traducción es incorrecta, el botón **Reportar traducción** (en el mensaje) la registra en la base de datos y le pide al paciente repetir la seña.

### Modo Captura

Sirve para grabar muestras nuevas y reentrenar.

1. En `/paciente`, botón **Ajustes (Modo Captura)**.
2. Elegir la seña (la lista sale de `GET /classes`, o sea de `models/custom_classes.json`) y la cantidad de **Repeticiones**.
3. **Empezar**: cuenta regresiva y grabación de 45 frames por muestra. Cada muestra se guarda como `.npy` en `<NEXORA_DATASET_DIR>/custom/<seña>/` (y los blendshapes en `custom_blendshapes/`).
4. Si la cámara procesó menos de 18 fps durante la grabación, la muestra se descarta con un aviso (ver `MIN_SAMPLE_FPS` en `web/components/capture/CaptureMode.tsx`, ajustable con `NEXT_PUBLIC_MIN_SAMPLE_FPS`). Cerrar otros programas que usen la GPU suele resolverlo.

### Entrenamiento y evaluación

```powershell
# Entrenar y guardar models/lstm.pth + models/custom_classes.json
python train_lstm.py

# Validación cruzada estratificada con k folds (no guarda el modelo)
python train_lstm.py --cv 5

# Evaluar el modelo actual contra un directorio con carpetas por seña
python eval_model.py <directorio_dataset>
```

Otras opciones de `train_lstm.py`: `--data-dir`, `--blendshapes`, `--out-prefix` (guarda un modelo experimental en vez del de producción), `--hand-local {0,1,2}` y `--seed`. Por defecto toma `<NEXORA_DATASET_DIR>/custom`. Reiniciar el backend después de entrenar para que cargue el modelo nuevo.

### Vocabulario actual

`cabeza`, `dolor`, `idle` (manos en reposo, cierra la oración), `respirar`, `yo`.

Fuente de las señas de referencia: diccionario Spreadthesign Argentina, <https://spreadthesign.com/es.ar/search/>.

## Dataset compartido (Google Drive)

Cada integrante graba en su PC con su propio backend y las muestras se sincronizan por una carpeta compartida de Google Drive para escritorio.

1. El dueño de la carpeta la comparte por email con cada integrante con rol **Editor**.
2. Cada integrante agrega un acceso directo a la carpeta en **Mi unidad** y la marca como **Disponible sin conexión**, para que Drive la mantenga sincronizada en disco.
3. En el `.env` de la raíz (copia de `.env.example`) completar:
   ```ini
   NEXORA_DATASET_DIR=G:\Mi unidad\Nexora\dataset
   NEXORA_RECORDER=santino
   ```
   `NEXORA_DATASET_DIR` apunta a la carpeta que contiene `custom/` y `custom_blendshapes/`. `NEXORA_RECORDER` es el nombre de quien graba (solo letras, números y guiones, máximo 32). Las muestras se guardan como `<timestamp>_<nombre>.npy`, así no chocan con las de los demás. Sin `NEXORA_RECORDER` el nombre es `<timestamp>.npy`; sin `NEXORA_DATASET_DIR` se usa `dataset/`.
4. El backend, `train_lstm.py` y `eval_model.py` leen el `.env` al iniciar.

Precauciones:

- Los borrados también se sincronizan para todos (la papelera de Drive conserva los archivos 30 días). No borrar muestras de otros integrantes.
- Esperar a que Drive termine de sincronizar antes de entrenar; de lo contrario el modelo usa un dataset incompleto.

## Tests

Detalle completo en [`tests/README.md`](tests/README.md).

**Scripts unitarios de la raíz** (con el venv activado, desde la raíz; cada uno corre por su bloque `__main__`):

```powershell
python test_storage.py
python test_features.py
python test_capture_validation.py
python test_report_validation.py
python test_capture_recorder.py
python test_audit.py
python test_infer.py   # requiere muestras en dataset/custom/
```

**Tests de API** (levantan su propio uvicorn en un puerto libre y una base temporal; requieren Ollama con `qwen2:1.5b`, si no los casos afectados quedan `blocked`):

```powershell
venv\Scripts\python.exe tests/api/run_all.py [TC-ID ...]
```

**Tests de UI** (Playwright, desde `tests/e2e`):

```powershell
cd tests\e2e
npm install
npx playwright install chromium
npx playwright test
```

Playwright levanta el backend en el puerto 8000 y el frontend en el 3000: el **8000 debe estar libre** (el 3000 se reutiliza si ya corre). Ejecutar las suites de a una, no en paralelo, para no pisar puertos. Resultados en `tests/api/results/` y `tests/e2e/results/`.

## Estructura del proyecto

```
app.py                 API FastAPI: REST, WebSocket /ws/predict, Ollama, Piper
storage.py             SQLite: reportes y auditoría
capture_validation.py  Validación de capturas, reportes y auditoría; lectura del .env
train_lstm.py          Entrenamiento y validación cruzada del LSTM
eval_model.py          Evaluación de un modelo contra un dataset
src/                   Features (src/features.py) y modelo (src/model/lstm.py)
models/                lstm.pth y custom_classes.json
voices/                Voz Piper (no versionada)
dataset/               Muestras .npy (o la carpeta de NEXORA_DATASET_DIR)
web/                   Frontend Next.js (app/, components/, hooks/, lib/)
tests/api/             Harness y casos de la API
tests/e2e/             Playwright
test_*.py              Scripts de prueba unitarios (raíz)
docs/                  Documentación académica (TP7, TP8)
```

## Problemas frecuentes

| Síntoma | Causa y solución |
|---------|------------------|
| `uvicorn` falla al importar módulos | Se ejecutó fuera de la raíz del repo. Lanzarlo siempre desde la raíz |
| No aparece la cámara | Revisar el permiso del sitio en Chrome y que ninguna otra aplicación la esté usando |
| Pocos fps / muestras descartadas | Sin aceleración de hardware de WebGL, MediaPipe cae a CPU y baja la tasa. Activar la aceleración por hardware de Chrome y cerrar programas que usen la GPU |
| Mensaje de consola sobre XNNPACK | Informativo, es inofensivo |
| Error CORS o la pantalla no conecta | Abrir el frontend por `localhost:3000` o `127.0.0.1:3000`, o agregar el origen a `NEXORA_ALLOWED_ORIGINS` |
| Sin audio | Falta `voices/es_AR-daniela-high.onnx`; ver [Instalación](#instalación) |
| El chat no se sincroniza | `BroadcastChannel` solo funciona entre pestañas del mismo navegador y perfil |
| Oraciones lentas la primera vez | Ollama carga el modelo en memoria en la primera consulta. Las coincidencias con plantilla o caché no lo usan |

Nota: el backend llama a Ollama en `127.0.0.1:11434` (no `localhost`) para evitar una demora de ~2 s por el intento previo con IPv6 en Windows.

## Documentación y equipo

- `docs/TP7/`: Análisis y Diseño (LaTeX, un entregable por archivo). Ver [`docs/README.md`](docs/README.md) para la estructura y `docs/IDS.md` para el registro de identificadores.
- `docs/TP8/`: Testing (plan, casos de prueba, defectos y observaciones por ciclo).

**Equipo (UTN-FRT):**

- Hamada, Santino
- García Tarcic, Iñaki Ezequiel
- Véliz, Héctor Matias
- Arnedo, Emmanuel Augusto
