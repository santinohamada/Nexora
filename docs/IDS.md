# IDS.md — Registro canónico de identificadores (LSA Salud)

Fuente única de verdad para IDs y nombres usados en los nueve entregables
académicos (Modelo de Dominio, Diagrama de Casos de Uso, Modelos de Casos
de Uso, Mockups, ERS IEEE 830, Arquitectura, Casos de Uso Reales, Diagramas
de Colaboración, Modelo de Datos) y el Documento Maestro. No renombrar ni
reordenar sin actualizar este archivo primero.

Alcance verificado contra código: `app.py`, `train_lstm.py`, `src/model/lstm.py`,
`capture_validation.py`, `web/app/**/page.tsx`, `web/hooks/*.ts`,
`web/lib/mediapipe.ts`, `web/components/**`, `README.md`.

> **Nota de nombre:** "Nexora" es el nombre del repositorio de código, no el
> nombre del proyecto académico. El proyecto y el sistema se llaman
> **LSA Salud** en todo documento formal.

---

## 0. Identidad del proyecto

| Campo | Valor |
|---|---|
| Nombre del proyecto / sistema | **LSA Salud** |
| ID de proyecto | `LSASALUD-G9` |
| Cliente | Sanatorio 9 de Julio (San Miguel de Tucumán) |
| Director de Proyecto | Hamada, Santino |
| Tutor | Vicente, Francisco José |
| Cotutor | López, Emmanuel |
| Cátedra / Institución | Proyecto Final — Departamento de Ingeniería en Sistemas de Información, UTN-FRT |
| Preparado por | Hamada, Santino · García Tarcic, Iñaki Ezequiel · Véliz, Héctor Matias · Arnedo, Emmanuel Augusto |

### Códigos de documento (esquema propio del equipo)

| Entregable | Código |
|---|---|
| 01 — Modelo de Dominio | `LSASALUD-G9-MD` |
| 02 — Diagrama de Casos de Uso | `LSASALUD-G9-DCU` |
| 03 — Modelos de Casos de Uso | `LSASALUD-G9-MCU` |
| 04 — Mockups | `LSASALUD-G9-MCK` |
| 05 — ERS (IEEE 830) | `LSASALUD-G9-ERS` |
| 06 — Arquitectura: Vistas | `LSASALUD-G9-ARQ` |
| 07 — Casos de Uso Reales | `LSASALUD-G9-CUR` |
| 08 — Diagramas de Colaboración | `LSASALUD-G9-DCO` |
| 09 — Modelo de Datos | `LSASALUD-G9-MBD` |
| TP7 Análisis y Diseño (documento maestro) | `LSASALUD-G9-DM` |

---

## 1. Actores

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| ACT-01 | Paciente | Primario | Persona sorda o hipoacúsica que se comunica mediante Lengua de Señas Argentina (LSA) frente a la cámara de la Estación del Paciente (`web/app/paciente/page.tsx`). Corresponde al interesado **"Personas que se comunican con LSA"**. |
| ACT-02 | Personal de Recepción o Enfermería | Primario | Personal de recepción o enfermería que lee la traducción del paciente y responde por texto o dictado de voz desde la Estación de Recepción (`web/app/recepcion/page.tsx`). **Generaliza explícitamente** a los interesados **"Recepcionista"** y **"Enfermero/a"** — porque ambos comparten el mismo requisito involucrado ("Traducción LSA→texto"), el mismo interés ("comunicación directa y privada con el paciente") y la misma estrategia de gestión ("Gestionar de Cerca"); no hay ninguna interacción con el sistema que distinga a uno de otro, por lo que modelarlos como actores separados duplicaría el mismo caso de uso sin aportar comportamiento distinto (Larman, *UML y Patrones*: generalizar actores solo cuando comparten objetivos y forma de interacción). |
| ACT-03 | Desarrollador de IA / Equipo de Proyecto | Primario | Personal técnico del equipo que graba nuevas muestras de señas (Modo Captura, `CaptureMode.tsx`) y reentrena el modelo LSTM (`train_lstm.py`). **Decisión de diseño del equipo**: no existe un rol de usuario final equivalente para esta tarea. La construcción de dataset y el entrenamiento son tareas del propio equipo del proyecto, no un rol operativo del producto entregado al Sanatorio. Se mantiene como actor de sistema — en vez de tratarse como trabajo puramente externo al software — porque el software realmente expone un Modo Captura en producción. |

No se modelan actores de sistema secundarios (LLM/Ollama, Piper TTS) porque
son componentes invocados sincrónicamente por el backend (`app.py`), sin
iniciativa propia ni interacción directa con una persona — no cumplen la
definición de actor de Larman/UML 2.5. Se documentan como dependencias
tecnológicas en la ERS (secciones 2.4 y 3.4).

No se modela un actor nuevo para el consumo de las métricas de auditoría del
RF-04 (logs de uso y métricas operativas). El registro es una subfunción
automática, incluida por CU-01 y CU-04 (ver CU-11), sin interacción humana
directa en el software; su consumo (lectura/exportación de esas métricas) es
un proceso organizacional fuera de la interfaz, y no una pantalla del
sistema. Dirección del Sanatorio, interesada en RF-04, es en consecuencia un
interesado de reporte, no un actor de sistema: es la opción más limpia según
Larman (evitar introducir un actor sin interacción concreta con el sistema
modelado).

---

## 2. Casos de uso

| ID | Nombre | Actor principal | Nivel | Relación |
|----|--------|------------------|-------|----------|
| CU-01 | Comunicarse mediante Lengua de Señas Argentina | Paciente | Objetivo de usuario | Base; incluye CU-02, CU-03 y CU-11; tiene como precondición CU-09 |
| CU-02 | Traducir Secuencia de Señas a Oración Natural | Paciente (vía sistema) | Subfunción | Incluido por CU-01 |
| CU-03 | Sintetizar Oración en Voz | Paciente (vía sistema) | Subfunción | Incluido por CU-01 |
| CU-04 | Responder al Paciente | Personal de Recepción o Enfermería | Objetivo de usuario | Base; extendido por CU-05; incluye CU-11 |
| CU-05 | Dictar Respuesta por Voz | Personal de Recepción o Enfermería | Subfunción | Extiende a CU-04 |
| CU-06 | Capturar Muestra de Seña para Entrenamiento | Desarrollador de IA / Equipo de Proyecto | Objetivo de usuario | Base; incluye CU-07 |
| CU-07 | Gestionar Vocabulario de Señas | Desarrollador de IA / Equipo de Proyecto | Subfunción | Incluido por CU-06 |
| CU-08 | Entrenar el Modelo de Reconocimiento | Desarrollador de IA / Equipo de Proyecto | Objetivo de usuario | Independiente (precondición: CU-06 ejecutado antes) |
| CU-09 | Otorgar Consentimiento Explícito de Cámara | Paciente | Objetivo de usuario | Precondición obligatoria de CU-01 (RF-03) |
| CU-10 | Reportar Traducción Incorrecta o Ambigua | Paciente, Personal de Recepción o Enfermería | Objetivo de usuario | Extiende a CU-01 y a CU-04 (punto de extensión: "revisión de mensaje") (RF-06) |
| CU-11 | Registrar Evento de Auditoría | (subfunción interna del sistema, sin actor humano) | Subfunción | Incluido por CU-01 y CU-04 (RF-04) |
| CU-12 | Finalizar Atención y Preparar la Estación para el Próximo Paciente | Personal de Recepción o Enfermería | Objetivo de usuario | Base; cierra la conversación abierta por CU-01/CU-04 (RNF-03) |

Paquetes del diagrama de casos de uso: **Comunicación** (CU-01 a CU-05,
CU-09, CU-10, CU-12), **Gestión del Modelo** (CU-06 a CU-08), **Auditoría**
(CU-11). El diagrama de casos de uso (Entregable 02) usa una única columna
dentro del límite del sistema, o dos si doce casos de uso no entran en una
columna legible (ver formato de referencia).

---

## 3. Requisitos funcionales

### 3.1 Requisitos funcionales base (RF-01 a RF-06)

Estos seis IDs están **reservados** para el texto base del requisito; no se
reescriben.

| ID | Descripción (texto literal) | Criterio de verificación | Cobertura en LSA Salud |
|---|---|---|---|
| RF-01 | El sistema debe traducir LSA a texto y voz en tiempo casi real. | Latencia percibida < 1 s en condiciones normales | Ver RF-01.1 a RF-01.8 |
| RF-02 | El sistema debe transcribir la voz o texto del profesional a un formato de texto accesible para el paciente sordo. | Mensaje entregado en pantalla en el mismo canal sincronizado que RF-01 | Ver RF-02.1, RF-02.2 |
| RF-03 | La interfaz debe desplegar una pantalla de consentimiento explícito obligatorio antes de activar la cámara. | Diálogo de consentimiento obligatorio previo a activar la cámara | Ver CU-09, RF-03.1 |
| RF-04 | El sistema debe registrar logs de uso internos y métricas operativas anónimas para auditoría. | 0% de datos identificatorios o imágenes/video en los registros de auditoría | Ver CU-11, RF-04.1 |
| RF-05 | El sistema debe detectar cuando una seña no pueda interpretarse con confianza y evitar mostrar una traducción incorrecta. | Accuracy ≥ 90% en entornos controlados y ≥ 85% en operación real | Mecanismo de umbral, ver RF-01.3, RF-01.4 |
| RF-06 | El sistema debe permitir que paciente o profesional reporten una traducción incorrecta/ambigua/no comprendida, para registrar el caso y mejorar el modelo. | Accuracy ≥ 90% en entornos controlados y ≥ 85% en operación real | Ver CU-10, RF-06.1 |

### 3.2 Sub-requisitos técnicos trazables

Cada uno es una realización parcial de su RF padre (relación muchos-a-uno).
Continúan la numeración `RF-<base>.<n>`.

| ID | Texto (una línea) | CU relacionados | Traza a RF |
|----|--------------------|------------------|---------------------|
| RF-01.1 | Captura en tiempo real de landmarks de manos, pose y rostro (blendshapes) desde la cámara mediante MediaPipe. Los blendshapes faciales aportan los marcadores no manuales gramaticales de la LSA (preguntas, negación, intensidad) como parte de las características de reconocimiento. | CU-01 | RF-01 |
| RF-01.2 | Envío de los frames acumulados al backend para predicción vía WebSocket. | CU-01 | RF-01 |
| RF-01.3 | Clasificación de la seña mediante el modelo LSTM sobre una ventana de 45 frames, con umbral de confianza del 70 %. | CU-01, CU-02 | RF-01 (mecanismo de umbral realiza también RF-05) |
| RF-01.4 | Construcción incremental de la secuencia de palabras y detección de cierre de oración por inactividad (idle ≥ 800 ms + quietud de movimiento); descarta señas de baja confianza o de reposo. | CU-01 | RF-01 (realiza también RF-05) |
| RF-01.5 | Traducción de la secuencia de palabras a una oración natural en español (plantilla médica → caché → modelo de lenguaje local). | CU-02 | RF-01 |
| RF-01.6 | Síntesis de voz de la oración traducida con acento argentino y reproducción tras una ventana de exhibición previa. | CU-03 | RF-01 |
| RF-01.7 | Publicación del mensaje traducido en la conversación sincronizada entre las dos caras de la estación. | CU-01, CU-04 | RF-01 (soporta también RF-02, como canal de entrega) |
| RF-01.8 | Verificación de fidelidad clínica: el módulo de traducción valida que la oración generada por el modelo de lenguaje no incorpore síntomas, medicamentos ni términos clínicos ausentes de la secuencia de señas reconocida, antes de mostrarla o sintetizarla. | CU-02 | RF-01 (realiza también RF-05) |
| RF-02.1 | Redacción y envío de una respuesta de texto por parte del personal de recepción o enfermería. | CU-04 | RF-02 |
| RF-02.2 | Dictado de la respuesta por voz (Web Speech API, es-AR), acumulable sobre texto ya escrito. | CU-05 | RF-02 |

### 3.3 Requisitos técnicos sin RF base directo (decisión de diseño del equipo)

Sin contraparte en la matriz de requisitos: sostienen CU-06/07/08 (gestión
del modelo), una decisión de arquitectura del equipo documentada en ACT-03
(sección 1) y en el Entregable 02. CU-06, CU-07 y CU-08 son, en conjunto,
las herramientas de administración del modelo y del dataset con las que
cuenta el Equipo de Proyecto (Modo Captura, gestión de vocabulario y
reentrenamiento); no se agrega una pantalla de administración adicional
fuera de estos tres casos de uso.

| ID | Texto (una línea) | CU relacionados |
|----|--------------------|------------------|
| RF-T-01 | Selección de una etiqueta de seña existente o creación de una etiqueta nueva antes de grabar una muestra. | CU-07 |
| RF-T-02 | Consulta de las clases reconocidas por el modelo y de las estadísticas de muestras por etiqueta del dataset activo. | CU-07 |
| RF-T-03 | Grabación de una o varias muestras de entrenamiento (45 frames) con cuenta regresiva y repeticiones configurables. | CU-06 |
| RF-T-04 | Persistencia de cada muestra grabada como archivo `.npy`, con los landmarks de manos y pose junto con los blendshapes faciales en un único árbol de captura. | CU-06 |
| RF-T-05 | Reentrenamiento offline del modelo LSTM a partir de las muestras capturadas, con separación entrenamiento/validación y guardado del mejor modelo. | CU-08 |
| RF-T-06 | Selección de la estación de trabajo (Paciente / Recepción) desde la página de inicio. | Precondición de CU-01 y CU-04 |

### 3.4 Sub-requisitos de consentimiento, auditoría y reporte

Cubren RF-03, RF-04 y RF-06.

| ID | Texto (una línea) | CU relacionados | Traza a RF |
|----|--------------------|------------------|---------------------|
| RF-03.1 | Antes de activar la cámara, el sistema despliega un diálogo de consentimiento explícito (`PacientePage`) y bloquea el acceso a la cámara (`enabled` en el hook de landmarks) hasta que el paciente lo otorgue. | CU-09 | RF-03 |
| RF-04.1 | El sistema registra, de forma automática y anónima, un evento de auditoría por cada operación de sistema relevante (predicción, traducción/síntesis, reporte, consentimiento, traducción mostrada, fin de atención), sin datos identificatorios ni imágenes/video, en la base de datos SQLite (`data/lsa_salud.db`). | CU-11 | RF-04 |
| RF-06.1 | El paciente o el personal de recepción/enfermería pueden marcar un mensaje del paciente como traducción incorrecta o ambigua (botón "Reportar traducción" en `ChatBubble`); el reporte y el mensaje se persisten en la base de datos SQLite (`data/lsa_salud.db`) y se notifica a ambas caras de la estación. | CU-10 | RF-06 |

CU-12 no agrega un sub-requisito RF propio: realiza directamente RNF-03 (ver
RNF-03.1 en la sección 4.2, actualizada con la acción de fin de atención) y
se apoya en RF-04.1 para registrar el evento de auditoría de cierre.

Total: **12 RF sub-requisitos** (RF-01.1–RF-01.8, RF-02.1–RF-02.2, RF-03.1,
RF-04.1, RF-06.1), **6 RF técnicos sin RF base** (RF-T-01–RF-T-06).

---

## 4. Requisitos no funcionales

### 4.1 Requisitos no funcionales base (RNF-01 a RNF-07)

| ID | Descripción (texto literal) | Criterio de verificación | Verificación en LSA Salud |
|---|---|---|---|
| RNF-01 | Latencia: procesamiento e interpretación de señas en tiempo real <1 segundo. | Latencia percibida < 1 s en condiciones normales | Verificada mediante las métricas operativas del sistema (`GET /metrics`, ver RNF-01.1) |
| RNF-02 | Precisión: accuracy mínimo 90% en entornos clínicos controlados. | Accuracy ≥ 90% en entornos controlados y ≥ 85% en operación real | Verificada con evaluación del modelo sobre un conjunto de prueba independiente (`eval_model.py`, ver RNF-02.1) |
| RNF-03 | Seguridad y Privacidad: 100% de interacciones de video procesadas sin almacenamiento persistente de imágenes/video. | 0% de almacenamiento persistente de video/imágenes | Verificada por diseño de arquitectura (ver RNF-03.1) |
| RNF-04 | Compatibilidad de Hardware: exclusivamente cámaras, pantallas doble cara y componentes comerciales estándar. | Hardware comercial estándar, sin equipamiento médico especializado | Verificada por el diseño de la estación fija (ver RNF-04.1) |
| RNF-05 | Especialización de Datos: dataset ampliado y adaptado al dominio clínico (síntomas, triaje, dolor). | Cobertura del vocabulario clínico del dataset | Verificada por la cobertura del vocabulario clínico del dataset (ver RNF-05.1) |
| RNF-06 | El dataset clínico LSA debe ser revisado y validado lingüísticamente por intérpretes antes de usarse como base final. | Dataset clínico validado por intérpretes de LSA | Verificada mediante acta de validación de los intérpretes (ver RNF-06.1) |
| RNF-07 | El sistema debe poder usarse en una estación fija de guardia/triaje con cámara, pantalla doble cara, micrófono y altavoces. | Hardware comercial estándar, sin equipamiento médico especializado | Verificada por el diseño de la estación fija (ver RNF-07.1) |

### 4.2 Sub-requisitos técnicos trazables

| ID | Atributo | Texto (una línea) | Traza a RNF | Verificación |
|----|----------|--------------------|----------------------|--------------|
| RNF-01.1 | Rendimiento | Metas de latencia extremo a extremo expresadas en p50/p95 (ver ERS 3.3): p50 ≤ 600 ms (ruta con plantilla), p95 ≤ 1 s (caso general). El sistema mide cada etapa mediante eventos de auditoría (`lstm_ms`, `translation_ms`, `tts_ms`, `total_ms`, `e2e_ms`) agregados por `GET /metrics`. | RNF-01 | Medición continua de p50/p95 sobre las métricas operativas agregadas por `GET /metrics` |
| RNF-02.1 | Precisión del modelo | Exactitud de validación del modelo LSTM (`ModeloDeReconocimiento.exactitudDeValidación`, ver Entregable 01), calculada durante `train_lstm.py` sobre el 20% de validación; `eval_model.py <directorio>` mide accuracy, precisión/recall y matriz de confusión sobre un directorio de muestras. | RNF-02 | Evaluación con `eval_model.py` sobre un conjunto de muestras independiente del entrenamiento |
| RNF-03.1 | Seguridad / privacidad | Todo el procesamiento y almacenamiento ocurre en la máquina local; no hay persistencia de conversaciones (estado en memoria, sincronizado entre las dos caras de la estación); los eventos de auditoría (RF-04.1) se registran sin imágenes ni video, consistentes con esta restricción. Al finalizar cada atención (CU-12), el sistema borra explícitamente la conversación en ambas caras. | RNF-03 | Verificada por diseño de arquitectura (sin persistencia) y por la acción de cierre de CU-12 |
| RNF-04.1 / RNF-07.1 | Compatibilidad de hardware / estación fija | Las dos caras sincronizadas de la estación (Paciente y Recepción), sobre el mismo navegador y canal de sincronización local, con doble monitor, **implementan las dos caras de la estación fija de guardia/triaje** exigida por RNF-04/RNF-07: cámara y pantalla del lado del paciente, pantalla y controles del lado del personal. El **ensamblaje físico** de esas dos pantallas y la cámara sobre hardware comercial (mostrador o box existente) y su calibración se realizan durante la instalación de cada estación (ver Entregable 06, Vista Física). | RNF-04, RNF-07 | Diseño de software completo; ensamblaje y calibración física verificados durante la instalación de cada estación |
| RNF-05.1 | Especialización de datos | El Modo Captura y el árbol de captura del dataset (`dataset/custom`) permiten ampliar continuamente el vocabulario clínico LSA (síntomas, triaje, dolor, admisión/recepción/guardia) a partir de un conjunto inicial de referencia. | RNF-05 | Verificada por la cobertura del vocabulario clínico del dataset, junto con la validación de intérpretes (RNF-06) |
| RNF-06.1 | Validación lingüística | La validación del dataset clínico por intérpretes de LSA es un procedimiento operativo del proyecto, realizado antes de incorporar cada ampliación del vocabulario al modelo en producción. | RNF-06 | Acta de validación firmada por los intérpretes participantes antes de cada actualización del dataset |

### 4.3 Requisitos técnicos sin RNF base directo

| ID | Atributo | Texto (una línea) |
|----|----------|--------------------|
| RNF-T-01 | Fiabilidad | El WebSocket de predicción se reconecta automáticamente cada 2 s; si el LLM local falla se usa el texto original; si Piper TTS no está disponible se omite el audio sin interrumpir el flujo. |
| RNF-T-02 | Disponibilidad | El sistema opera de forma autónoma en una PC local; el pipeline de reconocimiento y síntesis no requiere conectividad externa (Ollama y Piper corren localmente). |
| RNF-T-03 | Mantenibilidad | Responsabilidades separadas en hooks de React por función (cámara, WebSocket, chat, voz, construcción de oración) y modelo LSTM desacoplado del backend en un módulo propio. |
| RNF-T-04 | Portabilidad | Backend en Python 3.9+/FastAPI y frontend en Next.js 14/TypeScript, ambos multiplataforma; probado en Windows. Navegador soportado: Chrome (requerido por la Web Speech API de RF-02.2); el resto del pipeline no depende de APIs propietarias. |
| RNF-T-05 | Usabilidad / accesibilidad | Conversación fluida sin botones de confirmación manual (la ventana de exhibición previa a la voz actúa como confirmación automática); indicadores visuales de estado (en vivo, grabando, cuenta regresiva). |
| RNF-T-06 | Seguridad de red | El backend admite conexiones únicamente desde los orígenes configurados para la red local del sanatorio (restricción de CORS); no expone el servicio a redes externas. |

---

## 5. Conceptos del dominio (Modelo de Dominio)

| Concepto | Descripción breve |
|----------|--------------------|
| Paciente | Persona sorda/hipoacúsica que se comunica mediante LSA. |
| Personal de Recepción o Enfermería | Personal que atiende y responde al paciente. |
| Desarrollador de IA / Equipo de Proyecto | Personal técnico que amplía el vocabulario y reentrena el modelo. |
| EstaciónDeAtención | Pantalla/estación (Paciente o Recepción) sincronizada con la otra; sus dos caras físicas conforman una estación fija (RNF-04/07), desplegada de forma independiente en cada punto de atención del sanatorio (admisión, recepción, triaje, guardia). |
| Conversación | Intercambio de mensajes de una sesión de atención; se descarta por completo en las dos caras de la estación al finalizar la atención (CU-12), sin dejar datos persistidos. |
| Mensaje | Unidad de comunicación enviada por el paciente o el personal de recepción/enfermería. |
| SecuenciaDeSeñas | Secuencia de palabras reconocidas en curso, antes de traducirse. |
| ClaseDeSeña | Categoría de seña reconocible por el modelo (p. ej. "dolor"). |
| PalabraReconocida | Ocurrencia de una clase de seña detectada durante una secuencia, con su confianza. |
| Traducción | Resultado de convertir una secuencia de señas en una oración en español. |
| PlantillaMédica | Frase médica predefinida asociada a una combinación conocida de señas. |
| SíntesisDeVoz | Locución sonora asociada a un mensaje traducido. |
| ModeloDeReconocimiento | Red LSTM entrenada capaz de clasificar clases de seña. |
| MuestraDeEntrenamiento | Grabación de una seña capturada para (re)entrenar el modelo. |
| ConsentimientoDeCámara | Autorización explícita del paciente para activar la cámara, otorgada antes de iniciar CU-01 (RF-03); se realiza como un evento de auditoría de tipo `consent`, sin entidad ni archivo propios. |
| EventoDeAuditoría | Registro anónimo de una operación de sistema relevante, sin datos identificatorios ni imágenes/video (RF-04). |
| ReporteDeTraducción | Señalamiento de un mensaje del paciente como traducción incorrecta o ambigua, hecho por el paciente o el personal (RF-06). |

Diagrama de clases: `docs/TP7/diagramas/dominio/gen_modelo_dominio.py` → `docs/TP7/img/01_modelo_dominio.pdf`.
Diagrama de casos de uso: `docs/TP7/diagramas/02_casos_uso.puml` → `docs/TP7/img/02_casos_uso.pdf`.

---

## 6. Pantallas (mockups, Entregable 04)

| ID | Pantalla | Ruta | Componentes reales representados |
|----|----------|------|-----------------------------------|
| P-01 | Selección de Estación | `/` | `web/app/page.tsx` |
| P-02 | Estación del Paciente (modo predicción) | `/paciente` | `web/app/paciente/page.tsx`, `Header`, `TopPredictions`, `ChatBubble` |
| P-03 | Estación de Recepción | `/recepcion` | `web/app/recepcion/page.tsx`, `Header`, `ChatBubble`, `ReceptionControls` |
| P-04 | Modo Captura | `/paciente` (`mode === "capture"`) | `web/components/capture/CaptureMode.tsx` |
| P-05 | Diálogo de Consentimiento | `/paciente` (modal previo a activar la cámara) | `web/app/paciente/page.tsx` (diálogo inline en `PacientePage`, sin componente ni ruta propios) |

La Pantalla P-03 incluye, además, el control "Finalizar atención" (callout
nuevo) con el que el personal de recepción o enfermería ejecuta CU-12 desde
su propia cara de la estación.

Cada elemento anotado dentro de una pantalla usa un callout numerado en
círculo (①②③…), único por pantalla (no se reinicia entre secciones de la
misma pantalla). El Entregable 07 referencia estos callouts como
"panel ③ de la Pantalla P-02".

## 7. Operaciones de sistema y diagramas de colaboración (Entregable 08)

| ID | Operación de sistema | CU realizado | Diagrama de colaboración |
|----|------------------------|--------------|---------------------------|
| SO-01 | `reconocerSeña(frame)` | CU-01 (captura → buffer → predicción) | DC-01 |
| SO-02 | `cerrarOracionYTraducir(secuencia)` | CU-01 / CU-02 (cierre de oración y traducción) | DC-02 |
| SO-03 | `sintetizarVoz(oracion)` | CU-03 | DC-03 |
| SO-04 | `enviarRespuesta(mensaje)` | CU-04 (sincronización entre estaciones) | DC-04 |
| SO-05 | `capturarMuestra(frames, etiqueta)` | CU-06 | DC-05 |
| SO-06 | `otorgarConsentimiento(paciente)` | CU-09 | DC-06 |
| SO-07 | `registrarEventoAuditoria(operacion)` | CU-11 | DC-07 |
| SO-08 | `reportarTraduccion(mensaje)` | CU-10 | DC-08 |
| SO-09 | `limpiarConversacion()` | CU-12 (fin de atención, borrado sincronizado en ambas caras) | DC-09 |

Diagramas: `docs/TP7/diagramas/colaboracion/08_colaboracion_dc0N.drawio` → `docs/TP7/img/08_colaboracion_dc0N.pdf`.
