# Cobertura de casos de prueba - TP8, ciclo 1

Sistema: LSA Salud. Versión bajo prueba: `f29917a` (rama `master`). Catálogo: `docs/TP8/casos_prueba.json` (83 casos). Estrategia: caja negra funcional y de seguridad, según el plan modelo `PT-PFinal-2020-01-v2`.

Convenciones: los ids de caso se abrevian sin el prefijo `TC-LSA-` (por ejemplo `001-02`). El modo de ejecución figura entre paréntesis: `api` = automatizable sin navegador (HTTP, WebSocket y también líneas de comando del backend), `ui` = Playwright con Chromium y cámara falsa (los reconocimientos se simulan interceptando el WebSocket), `manual` = requiere una persona real o juicio humano. Los grupos 001 a 012 corresponden a CU-01 a CU-12; 013 a 015 son transversales (campo `cu` = `N/A`).

## 1. Resumen

| Modo | Casos | % |
|---|---:|---:|
| api | 36 | 43 % |
| ui | 34 | 41 % |
| manual | 13 | 16 % |
| **Total** | **83** | 100 % |

### Casos por grupo y modo

| Grupo | Descripción | api | ui | manual | Total |
|---|---|---:|---:|---:|---:|
| 001 | CU-01 Comunicarse mediante Lengua de Señas Argentina | 3 | 6 | 1 | 10 |
| 002 | CU-02 Traducir Secuencia de Señas a Oración Natural | 6 | 0 | 1 | 7 |
| 003 | CU-03 Sintetizar Oración en Voz | 3 | 1 | 1 | 5 |
| 004 | CU-04 Responder al Paciente | 0 | 3 | 0 | 3 |
| 005 | CU-05 Dictar Respuesta por Voz | 0 | 3 | 1 | 4 |
| 006 | CU-06 Capturar Muestra de Seña para Entrenamiento | 3 | 4 | 1 | 8 |
| 007 | CU-07 Gestionar Vocabulario de Señas | 2 | 2 | 0 | 4 |
| 008 | CU-08 Entrenar el Modelo de Reconocimiento | 2 | 0 | 0 | 2 |
| 009 | CU-09 Otorgar Consentimiento Explícito de Cámara | 0 | 4 | 0 | 4 |
| 010 | CU-10 Reportar Traducción Incorrecta o Ambigua | 4 | 3 | 1 | 8 |
| 011 | CU-11 Registrar Evento de Auditoría | 6 | 1 | 0 | 7 |
| 012 | CU-12 Finalizar Atención y Preparar la Estación para el Próximo Paciente | 0 | 3 | 0 | 3 |
| 013 | Privacidad y seguridad (RNF-03.1, RNF-T-06) | 3 | 1 | 0 | 4 |
| 014 | Rendimiento (RNF-01.1) | 3 | 1 | 1 | 5 |
| 015 | Calidad, estación fija y restricciones del sistema (RNF-02, RNF-04 a RNF-07, RNF-T-02, RNF-T-03, RNF-T-04, RNF-T-05) | 1 | 2 | 6 | 9 |
| | **Total** | **36** | **34** | **13** | **83** |

### Casos por categoría, tipo y prioridad

- **Categoría:** Funcional 58, Integridad de datos 9, Seguridad 8, Rendimiento 5, Usabilidad 3.
- **Tipo de prueba:** Funcional 52, Aceptación 17, Integridad 9, Unidad 5.
- **Prioridad:** Alta 48, Media 29, Baja 6.

## 2. Matriz de trazabilidad requisito - casos de prueba

### 2.1 Requisitos funcionales

| Requisito | Casos que lo cubren | Cant. |
|---|---|---:|
| RF-01 | 001-01 (manual), 014-05 (manual) | 2 |
| RF-01.1 | 001-01 (manual), 001-03 (ui), 013-02 (api), 015-06 (ui) | 4 |
| RF-01.2 | 001-01 (manual), 001-03 (ui), 001-06 (ui), 001-10 (api), 014-02 (api) | 5 |
| RF-01.3 | 001-01 (manual), 001-02 (api), 001-04 (ui), 001-08 (api), 014-02 (api), 015-02 (manual) | 6 |
| RF-01.4 | 001-01 (manual), 001-04 (ui), 001-05 (ui), 001-08 (api), 014-04 (ui) | 5 |
| RF-01.5 | 001-01 (manual), 001-02 (api), 001-05 (ui), 001-07 (ui), 002-01 (api), 002-02 (api), 002-03 (api), 002-04 (api), 002-06 (api), 002-07 (manual), 014-01 (api), 014-03 (api), 014-04 (ui) | 13 |
| RF-01.6 | 001-01 (manual), 001-02 (api), 003-01 (api), 003-02 (api), 003-03 (api), 003-04 (ui), 003-05 (manual), 014-01 (api), 014-04 (ui) | 9 |
| RF-01.7 | 001-01 (manual), 001-05 (ui), 003-04 (ui), 004-02 (ui), 010-01 (ui), 012-02 (ui), 013-03 (ui), 014-04 (ui) | 8 |
| RF-01.8 | 002-05 (api), 002-07 (manual) | 2 |
| RF-02 | 004-02 (ui) | 1 |
| RF-02.1 | 004-01 (ui), 004-02 (ui), 004-03 (ui), 005-01 (ui), 011-04 (ui), 013-03 (ui) | 6 |
| RF-02.2 | 005-01 (ui), 005-02 (ui), 005-03 (ui), 005-04 (manual) | 4 |
| RF-03 | 009-01 (ui), 009-02 (ui) | 2 |
| RF-03.1 | 009-01 (ui), 009-02 (ui), 009-03 (ui), 009-04 (ui), 011-01 (api) | 5 |
| RF-04 | 011-01 (api), 011-03 (api), 011-06 (api) | 3 |
| RF-04.1 | 001-02 (api), 009-01 (ui), 009-02 (ui), 011-01 (api), 011-02 (api), 011-03 (api), 011-04 (ui), 011-05 (api), 011-06 (api), 011-07 (api), 012-01 (ui), 013-01 (api) | 12 |
| RF-05 | 001-04 (ui), 001-08 (api), 002-05 (api), 015-02 (manual) | 4 |
| RF-06 | 010-01 (ui), 010-08 (manual) | 2 |
| RF-06.1 | 010-01 (ui), 010-02 (ui), 010-03 (ui), 010-04 (api), 010-05 (api), 010-06 (api), 010-07 (api), 010-08 (manual), 013-01 (api) | 9 |
| RF-T-01 | 006-03 (ui), 007-02 (ui), 007-03 (ui), 007-04 (api) | 4 |
| RF-T-02 | 006-01 (ui), 007-01 (api), 007-02 (ui) | 3 |
| RF-T-03 | 006-01 (ui), 006-02 (ui), 006-04 (ui), 015-04 (manual) | 4 |
| RF-T-04 | 006-01 (ui), 006-03 (ui), 006-05 (api), 006-06 (api), 006-07 (api), 006-08 (manual) | 6 |
| RF-T-05 | 008-01 (api), 008-02 (api), 015-01 (api) | 3 |
| RF-T-06 | 001-09 (ui) | 1 |

### 2.2 Requisitos no funcionales

| Requisito | Casos que lo cubren | Cant. |
|---|---|---:|
| RNF-01 | 001-01 (manual), 002-01 (api), 003-02 (api), 014-01 (api), 014-02 (api), 014-03 (api), 014-04 (ui), 014-05 (manual) | 8 |
| RNF-01.1 | 011-03 (api), 011-05 (api), 014-01 (api), 014-02 (api), 014-03 (api), 014-04 (ui) | 6 |
| RNF-02 | 008-01 (api), 015-01 (api), 015-02 (manual) | 3 |
| RNF-02.1 | 015-01 (api), 015-02 (manual) | 2 |
| RNF-03 | 004-03 (ui), 006-05 (api), 011-06 (api), 012-01 (ui), 012-02 (ui), 012-03 (ui), 013-01 (api), 013-02 (api), 013-03 (ui) | 9 |
| RNF-03.1 | 009-01 (ui), 009-02 (ui), 009-04 (ui), 010-01 (ui), 010-04 (api), 010-05 (api), 011-01 (api), 011-02 (api), 011-04 (ui), 011-06 (api), 012-01 (ui), 012-02 (ui), 013-01 (api), 013-02 (api), 013-03 (ui), 013-04 (api), 015-06 (ui) | 17 |
| RNF-04 | 015-03 (manual) | 1 |
| RNF-04.1 | 015-03 (manual) | 1 |
| RNF-05 | 006-01 (ui), 015-04 (manual) | 2 |
| RNF-05.1 | 015-04 (manual) | 1 |
| RNF-06 | 015-05 (manual) | 1 |
| RNF-06.1 | 015-05 (manual) | 1 |
| RNF-07 | 015-03 (manual) | 1 |
| RNF-07.1 | 015-03 (manual) | 1 |
| RNF-T-01 | 001-03 (ui), 001-06 (ui), 001-07 (ui), 001-10 (api), 002-03 (api), 002-04 (api), 003-03 (api), 009-03 (ui), 010-03 (ui), 011-07 (api) | 10 |
| RNF-T-02 | 002-04 (api), 015-06 (ui) | 2 |
| RNF-T-03 | 015-09 (manual) | 1 |
| RNF-T-04 | 005-01 (ui), 005-03 (ui), 005-04 (manual), 015-07 (manual) | 4 |
| RNF-T-05 | 001-01 (manual), 001-05 (ui), 003-04 (ui), 003-05 (manual), 004-02 (ui), 014-04 (ui), 015-08 (ui) | 7 |
| RNF-T-06 | 013-04 (api) | 1 |

Los requisitos base RF-01 a RF-06 y RNF-01 a RNF-07 se listan junto con sus sub-requisitos porque la ERS los menciona; RF-05 se verifica a través del mecanismo de umbral (RF-01.3, RF-01.4) y de la fidelidad clínica (RF-01.8).

## 3. Cobertura de escenarios y extensiones por caso de uso

Cada escenario principal y cada extensión de `03_modelos_casos_uso.tex` y `07_casos_uso_reales.tex` tiene al menos un caso.

| CU | Escenario / extensión | Casos |
|---|---|---|
| CU-01 | Escenario principal | 001-01, 001-02, 001-03, 001-05 |
| CU-01 | 3a. Seña bajo el umbral de certeza | 001-04, 001-08 |
| CU-01 | 3b. Seña de reposo (idle) | 001-04, 001-08 |
| CU-01 | 6a. Traducción no clara: no se genera mensaje | 001-07, 002-06 |
| CU-01 | 7a / 11a. Síntesis de voz no disponible | 003-03, 003-04 |
| CU-01 | 10b (real). Modelo de lenguaje no disponible: se muestran las palabras reconocidas | 002-04 |
| CU-01 | *a. Pérdida de conexión con el servicio de reconocimiento | 001-06 |
| CU-01 | Protocolo del WebSocket (JSON v1 / binario v2) y errores | 001-10 |
| CU-01 | Precondición: selección de estación (RF-T-06) | 001-09 |
| CU-02 | Escenario principal (plantilla) | 002-01, 002-02 |
| CU-02 | 3a1. Coincidencia en la caché de traducciones | 002-03 |
| CU-02 | 3a2. Delegación al modelo de lenguaje local | 002-03, 002-05, 002-07 |
| CU-02 | 3a2a. El modelo de lenguaje no responde o falla | 002-04 |
| CU-02 | 3a2b. El modelo determina que la combinación no es clara | 002-06 |
| CU-03 | Escenario principal | 003-01, 003-05 |
| CU-03 | 2a. Audio ya generado: reutilización | 003-02 |
| CU-03 | 3a. Motor de síntesis no cargado | 003-03, 003-04 |
| CU-04 | Escenario principal | 004-02, 004-01, 004-03 |
| CU-04 | 1a. Dictado por voz (extiende CU-05) | 005-01 |
| CU-04 | 5a. Reportar respuesta incorrecta (extiende CU-10) | 010-01, 010-02 |
| CU-05 | Escenario principal | 005-01, 005-02, 005-04 |
| CU-05 | 1a. Reconocimiento de voz no disponible | 005-03 |
| CU-05 | 2a. Error de micrófono o de reconocimiento | 005-03 |
| CU-06 | Escenario principal | 006-01, 006-02, 006-05, 006-06, 006-08 |
| CU-06 | 2a. Etiqueta nueva | 006-03 |
| CU-06 | 6a. Detener la grabación antes de tiempo | 006-04 |
| CU-07 | Escenario principal | 007-01, 007-02 |
| CU-07 | 4a. Creación y validación de etiqueta nueva | 007-02, 007-03, 007-04 |
| CU-08 | Escenario principal | 008-01, 015-01 |
| CU-08 | 2a. Sin clases ni muestras | 008-02 |
| CU-09 | Escenario principal | 009-01 |
| CU-09 | 3a. El paciente rechaza el consentimiento | 009-02 |
| CU-09 | 3b. Cámara denegada tras consentir | 009-03 |
| CU-10 | Escenario principal | 010-01, 010-02, 010-04 |
| CU-10 | 3a. Falla el envío del reporte | 010-03 |
| CU-11 | Escenario principal | 011-01, 011-03, 011-04 |
| CU-11 | Extensión: evento inválido no se registra sin interrumpir la operación | 011-02, 011-07 |
| CU-12 | Escenario principal | 012-01, 012-02 |
| CU-12 | 3a (real). La pantalla P-02 no estaba abierta | 012-03 |

## 4. Casos por caso de uso

| CU | Grupo | Casos | api | ui | manual |
|---|---|---:|---:|---:|---:|
| CU-01 | 001 | 10 | 3 | 6 | 1 |
| CU-02 | 002 | 7 | 6 | 0 | 1 |
| CU-03 | 003 | 5 | 3 | 1 | 1 |
| CU-04 | 004 | 3 | 0 | 3 | 0 |
| CU-05 | 005 | 4 | 0 | 3 | 1 |
| CU-06 | 006 | 8 | 3 | 4 | 1 |
| CU-07 | 007 | 4 | 2 | 2 | 0 |
| CU-08 | 008 | 2 | 2 | 0 | 0 |
| CU-09 | 009 | 4 | 0 | 4 | 0 |
| CU-10 | 010 | 8 | 4 | 3 | 1 |
| CU-11 | 011 | 7 | 6 | 1 | 0 |
| CU-12 | 012 | 3 | 0 | 3 | 0 |
| Transversal | 013-015 | 18 | 7 | 4 | 7 |

Los casos de grupos 011 y 013 se apoyan en CU-11 y RNF-03.1; los casos 004-02, 010-01 y 012-01 comparten la sincronización de RF-01.7.

## 5. Requisitos que no pueden cubrirse con prueba automática

Todos los RF de la ERS tienen al menos un caso. Las siguientes salvedades limitan el alcance de la evidencia:

- **RF-01.1 (captura en tiempo real) y RF-01.2 (envío de frames):** se verifican con cámara falsa, por lo que solo se comprueban la cadencia, el formato y el dibujo del canvas (001-03). Los landmarks de una persona real y su reconocimiento solo se evalúan en los casos `manual` 001-01 y 015-02. No se pueden verificar los blendshapes faciales por la ruta por defecto (ver D-09).
- **RF-02.2 (dictado):** la Web Speech API depende del servicio de voz del navegador y de Internet; los casos `ui` usan un doble de `SpeechRecognition`. La exactitud real del reconocimiento queda en 005-04 (`manual`).
- **RF-01.8 (fidelidad clínica):** el caso 002-05 es `api`, pero la valoración final de calidad lingüística requiere juicio humano (002-07, `manual`).
- **RNF-02 / RNF-02.1 (precisión):** `eval_model.py` sobre `dataset/custom` mide el conjunto de entrenamiento (015-01, `api`); la precisión real exige una sesión independiente (015-02, `manual`).
- **RNF-04 / RNF-04.1 / RNF-07 / RNF-07.1 (hardware y estación fija):** solo verificables por inspección física durante la instalación (015-03, `manual`).
- **RNF-05.1 / RNF-06.1 (dataset clínico y validación lingüística):** verificables por inspección del vocabulario y del acta de validación (015-04, 015-05, `manual`); el acta es un procedimiento organizacional y no es evidencia de software.
- **RNF-T-03 (mantenibilidad):** inspección de código (015-09, `manual`).
- **RNF-01 / RNF-01.1 (latencia):** 014-01 a 014-04 miden los percentiles en el backend y en la interfaz; el criterio de latencia percibida con una persona real queda en 014-05 (`manual`). Los valores dependen del hardware de la estación.

Ningún RF queda sin al menos un caso. No hay requisito funcional marcado como no cubrible; los casos `manual` mencionados arriba son la mejor evidencia disponible para esos aspectos.

## 6. Discrepancias detectadas

Las siguientes diferencias entre el análisis y diseño (TP7) y el comportamiento real del sistema son candidatas a defecto. Las marcadas como *verificada* se comprobaron ejecutando el backend (temporal, base SQLite aislada) con el comando HTTP/WebSocket indicado; las marcadas como *por confirmar* surgen de la lectura del código y deben confirmarse al ejecutar el caso asociado.

| Id | Estado | Descripción | Evidencia | Casos |
|---|---|---|---|---|
| D-01 | verificada (código) | CU-12 y la pantalla P-03 prevén un botón "Finalizar atención" que no existe. `RecepcionPage` no tiene control de borrado; el único control es "Limpiar Historial" en la pantalla del paciente (P-02). | `web/app/recepcion/page.tsx`, `web/app/paciente/page.tsx:330-335`; búsqueda de "Finalizar" sin resultados en `web/`. | 012-01 |
| D-02 | verificada | El evento de auditoría `fin_atencion` figura en el esquema SQLite y en RF-04.1, pero nadie lo registra: `POST /audit` solo admite `consent` y `translation_displayed` (responde 400 `Invalid audit type`) y el frontend no lo envía. | `capture_validation.py:15` (`AUDIT_TYPES`); respuesta observada `400 {"detail":"Invalid audit type"}`. | 011-02, 012-01 |
| D-03 | verificada (código) | CU-04 paso 6 y CU-11 exigen un evento de auditoría al enviar una respuesta del personal. `RecepcionPage` no llama a `sendAudit` y el esquema no tiene un tipo para ese evento. | `web/app/recepcion/page.tsx`, `storage.py:25-32`. | 011-04 |
| D-04 | verificada | RF-01.8 (verificación de fidelidad clínica) no está implementada: `app.py` solo instruye al modelo mediante el prompt y acepta cualquier salida. Para `yo brazo dolor` el modelo copió el ejemplo del prompt y se devolvió `Me duele el brazo. (NO agregues fiebre, ni cansancio, ni nada extra).` | `POST /process_sentence {"words":"yo brazo dolor"}` con Ollama caliente; ejemplo del prompt en `app.py:693-694`, sin verificación posterior en `app.py:704-728`. | 002-05 |
| D-05 | verificada | CU-02 3a2b y CU-01 10a: la traducción no clara debe descartarse. El backend sobreescribe el resultado con las palabras originales (también cuando el modelo responde `NO_CLARO`) y devuelve 200; el frontend solo filtra el literal `NO_CLARO`, que nunca recibe. Con `idle idle` se obtiene `natural_sentence: "idle idle"`. | `app.py:702,726-728`; `web/hooks/useSentenceBuilder.ts:120`. | 002-06, 001-07 |
| D-06 | verificada | RNF-T-06 / RNF-03.1: el backend debe admitir solo los orígenes de la red local, pero configura `allow_origins=["*"]`. Un origen ajeno recibe `Access-Control-Allow-Origin: *` y el preflight responde 200. | `app.py:36-41`; cabecera observada con `Origin: http://evil.example.com`. | 013-04 |
| D-07 | verificada | El protocolo WebSocket binario v2 es inalcanzable: `app.py` lee `scope["query"]` (clave inexistente en Starlette, la correcta es `query_string`), por lo que `?v=2` siempre se interpreta como v1 y un mensaje binario provoca `{"error": "'text'"}`. La ERS no menciona v2 y el frontend usa v1 por defecto; es código muerto o una funcionalidad rota. | `app.py:549-553`; respuesta observada al enviar un mensaje binario válido a `/ws/predict?v=2`. | 001-10 |
| D-08 | verificada (015-06) | RNF-T-02 y la restricción de ejecución local: la ruta de landmarks por defecto (`legacy`, `useMediaPipe`) carga `holistic.js`, `drawing_utils.js` y los archivos wasm desde `cdn.jsdelivr.net`. Sin Internet la cámara no termina de activarse. Solo `?mp=tasks` usa los archivos locales de `web/public/mediapipe`. | `web/hooks/useMediaPipe.ts:15-16,83-87`; `web/lib/mediapipe.ts`. Ejecución de 015-06 sin Internet: 2 intentos a `cdn.jsdelivr.net`, "Activando cámara..." permanece visible y no se envía ningún frame al backend. | 015-06 |
| D-09 | verificada (código) | RF-01.1 / RF-T-04 / glosario: los 52 blendshapes son características de reconocimiento y se guardan en un único árbol. En la ruta por defecto no se capturan; el modelo recibe solo 300 valores por frame (`input_size=300`); en modo `tasks` los blendshapes se guardan en `dataset/custom_blendshapes`, separados de `dataset/custom_tasks`, y no se envían al predictor. | `web/app/paciente/page.tsx:121-147`, `app.py:375-411`, `src/model/lstm.py:5`. | 006-05, 001-03 |
| D-10 | verificada | RF-T-04: `/capture` no valida la forma (T, 75, 4). Con 5 frames de 2x2 responde 200 y guarda un `.npy` corrupto que rompe `train_lstm.py`; con listas irregulares responde 500. `/predict` con forma inválida responde 500, y por `/ws/predict` un NaN devuelve `confidence: NaN` (JSON inválido). | Pruebas HTTP/WebSocket al backend aislado. | 006-07 |
| D-11 | verificada (código) | CU-07 4a / RF-T-01: la interfaz no valida el patrón de la etiqueta (solo recorta y pasa a minúsculas) y `recordOneSample` ignora la respuesta de `/capture`, por lo que una etiqueta inválida (por ejemplo con espacios) termina en "¡Guardado!" sin guardar nada. Con Repeticiones negativas también se muestra "¡Guardado!" sin grabar. | `web/components/capture/CaptureMode.tsx:121-135,137-154,167-180`. | 007-03, 006-02 |
| D-12 | verificada (006-04) | CU-06 6a: "Detener" no aborta `recordOneSample` ni el bucle de repeticiones; tras detener durante la grabación se envía a `/capture` la muestra parcial (se guarda si tiene 5 o más frames) y la secuencia continúa. | `web/components/capture/CaptureMode.tsx:104-135,156-165`. Ejecución de 006-04: tras "Detener" en la cuenta regresiva la secuencia continúa y se envía 1 muestra a `/capture`; al detener grabando se envía una muestra parcial de 5 frames. | 006-04 |
| D-13 | verificada (código) | CU-09 3b: con la cámara denegada el hook fija `status="error"` pero la pantalla no muestra ningún mensaje al paciente. | `web/hooks/useMediaPipe.ts:280-285`; `web/app/paciente/page.tsx` (solo renderiza el estado `loading`). | 009-03 |
| D-14a | por confirmar (005-02) | CU-05: con varios segmentos finales en una sesión de dictado continuo, `useSpeechToText` entrega solo el texto de los resultados nuevos y `ReceptionControls` reemplaza el contenido, por lo que se pierde el segmento anterior. Ejecución de 005-02 con dos resultados finales: el área contiene "y su credencial" en lugar de "necesito su documento y su credencial". | `web/hooks/useSpeechToText.ts:26-55`, `web/components/reception/ReceptionControls.tsx:14-31`. | 005-02 |
| D-14b | verificada (005-03) | CU-05: sin soporte del navegador se muestran dos avisos simultáneos: "El navegador no soporta reconocimiento de voz." y "Error de micrófono: Tu navegador no soporta el reconocimiento de voz. Intentá usar Google Chrome.". El caso 005-03 se aprobó porque el aviso exigido está presente; el duplicado es una observación. | `web/hooks/useSpeechToText.ts:26-55`, `web/components/reception/ReceptionControls.tsx:64-73`. | 005-03 |
| D-15 | verificada | RNF-01.1: el p95 de 1 s del caso general no es alcanzable por la ruta con modelo de lenguaje: con Ollama caliente la traducción tardó entre 2.3 y 4.7 s; con Ollama frío superó el tiempo de espera de 8 s y devolvió las palabras originales (latency_ms de ~10 400 ms). Además, por diseño el audio comienza al menos ~1.8 s después de bajar las manos (800 ms de quietud + 1000 ms de ventana de exhibición), lo que tensiona el criterio de latencia percibida < 1 s de RNF-01. | `/process_sentence` con combinaciones sin plantilla; `app.py:704-713`; `web/hooks/useSentenceBuilder.ts`. | 014-03, 014-05, 002-04 |
| D-16 | verificada | `GET /metrics?since=` rechaza con 400 `Invalid since timestamp` una marca ISO 8601 con sufijo `Z` (formato de `Date.toISOString()`) porque `datetime.fromisoformat` de Python 3.10 no lo admite. | `app.py:464-472`; observado con `since=2099-01-01T00:00:00Z`. | 011-05 |
| D-17 | verificada | RF-06.1 / RF-04.1: Pydantic convierte antes de la validación propia. `message_id=true` (boolean) y `message_id="12"` (cadena) se aceptan con 200; `e2e_ms="5"` y `true` también. La comprobación de booleanos de `validate_report_payload` es inalcanzable. | `capture_validation.py:44-48`; respuestas observadas. | 010-06, 011-02 |
| D-18 | por confirmar | RNF-T-04 declara Python 3.9+, pero `app.py` y `storage.py` usan anotaciones `X | None` evaluadas al definir funciones, que requieren Python 3.10; con 3.9 la importación fallaría. El entorno de pruebas usa Python 3.10.11. | `app.py:254` (`-> str | None`), `app.py:300,308-309,441-442` y `storage.py`. | 015-07 |
| D-19 | verificada (código) | La interfaz usa la marca "Nexora" (logo con texto alternativo "NEXORA Logo" y título "Bienvenido a Nexora") mientras la documentación formal nombra el sistema LSA Salud. | `web/app/page.tsx:18-19`, `web/components/layout/Header.tsx`. | 001-09 |
| D-20 | verificada | RNF-05 / ERS: el modelo reconoce solo 4 señas (`cabeza`, `dolor`, `respirar`, `yo`) más `idle`; las plantillas para `ayuda`, `doctor` y `revisar` son inalcanzables (el propio código lo indica). La ERS describe un dataset ampliado al dominio clínico (síntomas, triaje, admisión). | `GET /classes`; `app.py:236-244`. | 015-04 |
| D-21 | verificada (código) | Diferencias menores de texto respecto del TP7: indicador "← Click para hablar" (TP7: "Click para hablar"); botón "Nueva seña" (TP7: "+ Nueva seña"); umbral >= 70 (CU-01 real dice "supera el 70 %"); el selector muestra "Seña a grabar:". Conviene alinear el documento o la interfaz. | `web/components/reception/ReceptionControls.tsx:87`, `web/components/capture/CaptureMode.tsx:216-222`, `web/app/paciente/page.tsx:109`. | 005-01, 001-04 |
| D-22 | verificada | Inconsistencia de modos: `POST /capture` trata un `mode` desconocido como `legacy`, pero `GET /dataset_stats?mode=x` lo trata como `tasks`. | `app.py:366,385`. | 007-01, 006-05 |
| D-23 | verificada (005-01) | CU-05: el dictado sobrescribe el texto que la recepcionista ya escribió. Con "Buenos días" en el área de texto y una transcripción parcial "pase", el área queda con "pase" en lugar de "Buenos días pase". La instancia de `SpeechRecognition` iniciada conserva una clausura obsoleta con `baseText=""`, y el botón de detener actúa sobre otra instancia, no iniciada. | `web/hooks/useSpeechToText.ts`, `web/components/reception/ReceptionControls.tsx`; ejecución de 005-01 con doble de `SpeechRecognition`. | 005-01 |
| D-24 | verificada (014-01, 014-04); depende del entorno | RNF-01.1: incluso en la ruta con plantilla (sin modelo de lenguaje) el p95 de `latency_ms` agrupado fue 1356 ms (3 corridas, n=39; corridas individuales entre 791 y 1660 ms), por encima de la meta de 1000 ms, y en la prueba de sincronización de pantallas el tiempo de extremo a extremo (`e2e_ms`) tuvo p50 de 1526 ms (meta del caso: 600 ms). La medición se hizo con la suite de interfaz compartiendo la máquina (AMD Ryzen 3 3100), por lo que debe repetirse en una estación dedicada antes de cerrar el defecto. | Resultados de 014-01 (`tests/api/results/api-results.json`) y 014-04 (`tests/e2e/results/ui-summary.json`). | 014-01, 014-04 |
| D-25 | verificada (015-08) | Accesibilidad (RNF-05 / buenas prácticas): el análisis automático con axe-core detecta 6 violaciones graves o críticas: `color-contrast` (serious) en `/`, `/paciente` (x4), `/recepcion` (x2) y Modo Captura (x4); `button-name` (critical) en `/recepcion` (un botón sin nombre accesible); `label` (critical) en Modo Captura (un campo sin etiqueta asociada). | Ejecución de 015-08 con axe-core sobre `/`, `/paciente`, `/recepcion` y Modo Captura. | 015-08 |

## 7. Observaciones y puntos inciertos

- **Entorno de ejecución:** los casos `ui` requieren Playwright con Chromium (`--use-fake-device-for-media-stream`). La ruta `legacy` de MediaPipe necesita Internet (D-08); si el entorno de pruebas no tiene acceso a `cdn.jsdelivr.net`, esos casos quedarán bloqueados salvo que se use `?mp=tasks`.
- **Simulación de reconocimiento en `ui`:** los casos 001-04 a 001-07, 003-04 y 014-04 sustituyen el WebSocket con `page.routeWebSocket`. Verifican la lógica del frontend (umbral, idle, duplicados, cierre por quietud, sincronización), no el reconocimiento. El reconocimiento real con muestras del dataset se prueba en `api` (001-02, 001-08) y con personas en `manual`.
- **Modelo de lenguaje:** las salidas de Ollama no son deterministas; los casos 002-03, 002-05, 002-06 y 014-03 verifican propiedades (fuente, ausencia de términos ajenos, latencia) y no textos exactos. Un Ollama frío puede superar los 8 s y degradar a las palabras originales.
- **Datos de prueba:** las muestras de `dataset/custom` pertenecen al conjunto de entrenamiento (100 de 100 correctas con confianza >= 70 %); no miden generalización.
- **Efectos sobre el dataset real:** los casos de captura y entrenamiento deben ejecutarse con etiquetas `zz_tc_*` y sobre una copia del repositorio; 008-01 sobrescribe `models/custom_classes.json` y crea `models/lstm_v1_45frames.pth`, que `app.py` prioriza sobre `models/lstm.pth`.
- **Clasificación del entrenamiento (008-01, 008-02, 015-01):** se clasificó como `api` por ser automatizable por línea de comandos sin intervención humana, aunque no usa HTTP.
- **Hallazgos por confirmar:** D-14a y D-18 se deducen del código y deben confirmarse (D-08 y D-12 quedaron verificados con la ejecución de 015-06 y 006-04); el resto se observó con el backend en ejecución. La verificación del mockup de P-03 (`04_mockups.tex`) no se repitió: se tomó "Finalizar atención" de `IDS.md` y `07_casos_uso_reales.tex`.
- **Fuera de alcance del catálogo:** la ruta `/parity` (`web/app/parity/page.tsx`) existe en el código pero no figura en los documentos del TP7; no se diseñaron casos para ella.
