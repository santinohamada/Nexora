# Nexora (LSA Salud)

Sistema local de traducción de Lengua de Señas Argentina (LSA) a texto y voz para la recepción de un centro de salud. El paciente hace señas frente a una cámara; el sistema las reconoce, arma una oración en español, la muestra y la reproduce en voz alta. Recepción responde por texto o dictado. Todo corre en la propia PC (sin servicios en la nube para el reconocimiento, el LLM ni la voz).

Son dos pantallas del navegador que se sincronizan entre sí:

| Pantalla | URL | Uso |
|----------|-----|-----|
| Inicio | `http://localhost:3000/` | Acceso a las dos estaciones y a Captura |
| Estación del Paciente | `http://localhost:3000/paciente` | Cámara, reconocimiento de señas, chat |
| Estación de Recepción | `http://localhost:3000/recepcion` | Lee lo que dice el paciente y responde por teclado o voz |
| Modo Captura (uso interno) | `http://localhost:3000/captura` | Grabar muestras y reentrenar el modelo |

## Contenido

- [Cómo funciona](#cómo-funciona)
- [Requisitos](#requisitos)
- [Instalación y ejecución](#instalación-y-ejecución)
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

| Para usar Nexora | Para desarrollar o entrenar |
|----------------|----------------------------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (o Docker Engine + Compose) | Python 3.10, Node.js (>= 22.5 para tests de UI) |
| Google Chrome (cámara, voz, MediaPipe) | Ollama con `qwen2:1.5b` si corrés el backend a mano |

Los pesos del LSTM (`models/lstm.pth`) y las clases (`models/custom_classes.json`) están en el repo.

## Instalación y ejecución

### Con Docker (recomendado)

Cloná el repo, entrá a la raíz y levantá el stack. El puerto **3000** del host tiene que estar libre.

```powershell
git clone https://github.com/santinohamada/Nexora.git
cd Nexora
docker compose up --build
```

Abrí **http://localhost:3000**. La primera vez puede tardar varios minutos: construye las imágenes, baja MediaPipe, la voz Piper, Ollama y el modelo `qwen2:1.5b`. Todo corre en CPU. El navegador solo habla con el puerto 3000 (proxy Caddy → frontend y API); no hace falta instalar Python, Node ni Ollama en el host.

Las grabaciones, el modelo reentrenado y la base SQLite se guardan en `dataset/`, `models/` y `data/` del repo (Compose monta esas carpetas en el contenedor).

```powershell
docker compose down          # apagar
docker compose logs -f api   # logs del backend
```

En **Modo Captura** podés usar **Reentrenar modelo** sin salir del navegador. Para entrenar a mano: `python train_lstm.py` en el host (con el venv) y reiniciar el contenedor `api` si no usás el botón.

### Sin Docker (desarrollo)

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
cd web && npm install && cd ..
ollama pull qwen2:1.5b
```

Voz Piper: descargar `es_AR-daniela-high.onnx` y su `.json` desde [Hugging Face](https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_AR/daniela/high) a `voices/`. MediaPipe: `npm run dev` / `npm run build` en `web/` lo descargan solos.

Tres terminales (desde la raíz, con el venv activado en la del backend):

```powershell
ollama serve
python -m uvicorn app:app --port 8000
cd web && npm run dev
```

Variables opcionales por entorno o en un `.env` en la raíz (lo carga `python-dotenv`; no es obligatorio): `NEXORA_DATASET_DIR` (por defecto `dataset/`), `NEXORA_DB_PATH`, `NEXORA_ALLOWED_ORIGINS`, `OLLAMA_URL`. En el frontend manual, `web/.env.local` puede definir `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL` y `NEXT_PUBLIC_MIN_SAMPLE_FPS`.

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

1. Abrí `/captura`.
2. Completar **Tu nombre** (va en el archivo: `<timestamp>_<nombre>.npy`).
3. Elegir la seña (lista de `GET /classes` y `GET /dataset_stats`) y **Repeticiones**.
4. **Empezar**: cuenta regresiva y 45 frames por muestra en `dataset/custom/<seña>/` (blendshapes en `dataset/custom_blendshapes/`).
5. **Reentrenar modelo** cuando haya muestras nuevas; al terminar, la pantalla avisa que el reconocimiento volvió a estar listo.
6. Si la cámara procesó menos de 18 fps, la muestra se descarta (ver `MIN_SAMPLE_FPS` en `CaptureMode.tsx`).

### Entrenamiento y evaluación

```powershell
# Entrenar y guardar models/lstm.pth + models/custom_classes.json
python train_lstm.py

# Validación cruzada estratificada con k folds (no guarda el modelo)
python train_lstm.py --cv 5

# Evaluar el modelo actual contra un directorio con carpetas por seña
python eval_model.py <directorio_dataset>
```

Otras opciones de `train_lstm.py`: `--data-dir`, `--blendshapes`, `--out-prefix`, `--hand-local {0,1,2}` y `--seed`. Por defecto usa `dataset/custom`. Con el botón **Reentrenar modelo** en la UI no hace falta reiniciar el backend.

### Vocabulario actual

`cabeza`, `dolor`, `idle` (manos en reposo, cierra la oración), `respirar`, `yo`.

Fuente de las señas de referencia: diccionario Spreadthesign Argentina, <https://spreadthesign.com/es.ar/search/>.

## Dataset compartido (Google Drive)

Cada integrante graba en su PC con su propio backend y las muestras se sincronizan por una carpeta compartida de Google Drive para escritorio.

1. El dueño de la carpeta la comparte por email con cada integrante con rol **Editor**.
2. Cada integrante agrega un acceso directo a la carpeta en **Mi unidad** y la marca como **Disponible sin conexión**, para que Drive la mantenga sincronizada en disco.
3. Sincronizá la carpeta `dataset/` del repo con la compartida (o apuntá `NEXORA_DATASET_DIR` en el entorno del proceso si usás otra ruta). En Modo Captura cada uno pone su nombre en la pantalla; los archivos quedan como `<timestamp>_<nombre>.npy`.
4. Antes de **Reentrenar modelo** o `train_lstm.py`, esperá a que Drive termine de sincronizar.

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

`test_fidelity.py` usa estilo pytest (sin bloque `__main__`): `python -m pytest test_fidelity.py`. `pytest` no está en `requirements.txt`.

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
capture_validation.py  Validación de capturas, reportes y auditoría; rutas del dataset
train_lstm.py          Entrenamiento y validación cruzada del LSTM
eval_model.py          Evaluación de un modelo contra un dataset
src/                   Features (src/features.py) y modelo (src/model/lstm.py)
models/                lstm.pth y custom_classes.json
data/                  Base SQLite lsa_salud.db (no versionada)
docker-compose.yml     Stack Docker (ollama, api, web, proxy); Dockerfile y docker/ (Caddy, entrypoint)
voices/                Voz Piper (no versionada)
dataset/               Muestras .npy (custom/ y custom_blendshapes/)
web/                   Frontend Next.js (app/, components/, hooks/, lib/)
tests/api/             Harness y casos de la API
tests/e2e/             Playwright
test_*.py              Scripts de prueba unitarios (raíz)
docs/                  Documentación académica (TP7, TP8, TP9, informe final en ProyectoFinal/)
```

## Problemas frecuentes

| Síntoma | Causa y solución |
|---------|------------------|
| `uvicorn` falla al importar módulos | Se ejecutó fuera de la raíz del repo. Lanzarlo siempre desde la raíz |
| No aparece la cámara | Revisar el permiso del sitio en Chrome y que ninguna otra aplicación la esté usando |
| Pocos fps / muestras descartadas | Sin aceleración de hardware de WebGL, MediaPipe cae a CPU y baja la tasa. Activar la aceleración por hardware de Chrome y cerrar programas que usen la GPU |
| Mensaje de consola sobre XNNPACK | Informativo, es inofensivo |
| Error CORS o la pantalla no conecta (modo manual) | Usar `http://localhost:3000` o agregar el origen a `NEXORA_ALLOWED_ORIGINS`. Con Docker Compose no aplica: todo entra por el 3000 |
| Sin audio (modo manual) | Falta la voz en `voices/`; ver [Sin Docker](#sin-docker-desarrollo). Con Docker, revisar `docker compose logs api` |
| Puerto 3000 ocupado | Detener `npm run dev` u otro proceso en el 3000 antes de `docker compose up` |
| El chat no se sincroniza | `BroadcastChannel` solo funciona entre pestañas del mismo navegador y perfil |
| Oraciones lentas la primera vez | Ollama carga el modelo en memoria en la primera consulta. Las coincidencias con plantilla o caché no lo usan |

Nota (modo manual): por defecto Ollama está en `127.0.0.1:11434` (no `localhost`) para evitar demora por IPv6 en Windows. En Docker Compose se usa `OLLAMA_URL=http://ollama:11434`.

## Documentación y equipo

- `docs/TP7/`: Análisis y Diseño (LaTeX, un entregable por archivo). Ver [`docs/README.md`](docs/README.md) para la estructura y `docs/IDS.md` para el registro de identificadores.
- `docs/TP8/`: Testing (plan, casos de prueba, defectos y observaciones por ciclo).
- `docs/TP9/`: Informe final y presentación del trabajo práctico.
- `docs/ProyectoFinal/`: Informe del proyecto final (LaTeX, `latexmk -pdf`).

**Equipo (UTN-FRT):**

- Hamada, Santino
- García Tarcic, Iñaki Ezequiel
- Véliz, Héctor Matias
- Arnedo, Emmanuel Augusto
