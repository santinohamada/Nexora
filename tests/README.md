# Tests TP8

Las pruebas no tocan `data/lsa_salud.db`: usan una base SQLite temporal (`NEXORA_DB_PATH`) y una copia temporal del arbol de ejecucion.

## Prerrequisitos

- Python: venv del proyecto en la raiz (`venv\Scripts\python.exe` en Windows, `venv/bin/python` en otros sistemas) con las dependencias de `requirements.txt` instaladas.
- Node.js >= 22.5 (se requiere `node:sqlite`).
- Dependencias de Node: `npm install` en `web/` y en `tests/e2e/`.
- Navegador de Playwright: `npx playwright install chromium` (en `tests/e2e/`).
- Ollama en ejecucion (`localhost:11434`) con el modelo `qwen2:1.5b` (`ollama pull qwen2:1.5b`). Sin Ollama, los casos que lo requieren quedan como `blocked`.
- `voices/` en la raiz del repo: modelo de voz Piper (`es_AR-daniela-high.onnx` y su `.json`). No esta versionado; se obtiene del equipo. Si falta, los casos de TTS de la API quedan `blocked` y el backend de UI corre sin audio.

## Tests de API
Desde la raiz del repo:

    venv\Scripts\python.exe tests/api/run_all.py [TC-ID ...]

- Levanta uvicorn en un puerto libre con DB temporal, corre los casos registrados con `@tc("TC-...")` y lo apaga.
- Casos nuevos: crear `tests/api/test_*.py` e importarlo en `run_all.py`.
- Helpers en `tests/api/harness.py`: `http()`, `sample(label)`, `send_sequence(url, frames)`.
- Un caso sin ninguna verificacion (`Check.ok`/`Check.eq`) se registra como `fail` ("sin verificaciones").
- Resultados: `tests/api/results/api-results.json` (id, status pass/fail/blocked, observed, duration_s). `corrida_anterior` e `inestable` solo se calculan contra una corrida del mismo commit; de lo contrario quedan en `null`.
- Nota: `send_sequence(..., binary=True)` (protocolo `?v=2`) falla hoy porque app.py lee `scope["query"]` (no existe; deberia ser `query_string`), asi que el servidor siempre usa JSON v1.

## Tests de UI (Playwright)
Desde `tests/e2e`:

    npx playwright test [-g "TC-LSA-009-03"]
    node make-summary.mjs [reporte.json] [reporte-corrida-anterior.json]

- Playwright levanta solo el backend (puerto 8000, DB en `tests/e2e/.tmp/test.db`, cwd en la copia `tests/e2e/.tmp/runtime`) y el frontend (`npm run dev`, puerto 3000). El puerto 8000 debe estar libre; el 3000 se reutiliza si ya corre.
- Interprete de Python del backend: variable `PYTHON` si existe; si no, `venv/Scripts/python.exe` (Windows) o `venv/bin/python`.
- Camara y microfono falsos de Chromium (sin hardware).
- Resultados crudos: `tests/e2e/results/ui-results.json`; trazas en `tests/e2e/test-results/`.
- `make-summary.mjs` lee `docs/TP8/casos_prueba.json` (casos con `ejecucion: "ui"`) y genera `tests/e2e/results/ui-summary.json` a partir del reporte indicado (por defecto `ui-results.json`). Reconstruye el resumen completo desde ese unico reporte: los casos ausentes figuran como `blocked`, por lo que debe ejecutarse la suite completa antes. El segundo argumento (reporte de otra corrida) permite calcular `stable_between_runs`.
