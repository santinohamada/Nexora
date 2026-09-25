# IDS.md — Registro canónico de identificadores (LSA Salud)

Fuente única de verdad para IDs y nombres usados en los nueve entregables
académicos (Modelo de Dominio, Diagrama de Casos de Uso, Modelos de Casos
de Uso, Mockups, ERS IEEE 830, Arquitectura, Casos de Uso Reales, Diagramas
de Colaboración, Modelo de Datos) y el Documento Maestro. No renombrar ni
reordenar sin actualizar este archivo primero.

Alcance verificado contra código: `app.py`, `train_lstm.py`, `src/model/lstm.py`,
`capture_validation.py`, `web/app/**/page.tsx`, `web/hooks/*.ts`,
`web/lib/mediapipe.ts`, `web/components/**`, `README.md`. Alcance verificado
contra documentos oficiales de cátedra: `docs/referencias/RESUMEN_REFERENCIAS.md`
(digesto de TP0, TP1, TP2, EDT, Registro de Interesados, Matriz de Requisitos,
Registro de Riesgos).

> **Nota de nombre:** "Nexora" es el nombre del repositorio de código, no el
> nombre del proyecto académico. El proyecto y el sistema se llaman
> **LSA Salud** en todo documento formal (TP0/TP1/TP2 y estos entregables).

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

### Códigos de documento (esquema propio del equipo, no oficial)

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
| Documento Maestro | `LSASALUD-G9-DM` |

---

## 1. Actores

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| ACT-01 | Paciente | Primario | Persona sorda o hipoacúsica que se comunica mediante Lengua de Señas Argentina (LSA) frente a la cámara de la Estación del Paciente (`web/app/paciente/page.tsx`). Corresponde al interesado oficial **"Personas que se comunican con LSA"** (Registro de Interesados). |
| ACT-02 | Personal de Recepción o Enfermería | Primario | Personal de recepción o enfermería que lee la traducción del paciente y responde por texto o dictado de voz desde la Estación de Recepción (`web/app/recepcion/page.tsx`). **Generaliza explícitamente** a los dos interesados oficiales separados en el Registro de Interesados — **"Recepcionista"** y **"Enfermero/a"** — porque ambos comparten el mismo requisito involucrado ("Traducción LSA→texto"), el mismo interés ("comunicación directa y privada con el paciente") y la misma estrategia de gestión ("Gestionar de Cerca"); no hay ninguna interacción con el sistema que distinga a uno de otro, por lo que modelarlos como actores separados duplicaría el mismo caso de uso sin aportar comportamiento distinto (Larman, *UML y Patrones*: generalizar actores solo cuando comparten objetivos y forma de interacción). |
| ACT-03 | Desarrollador de IA / Equipo de Proyecto | Primario | Personal técnico del equipo que graba nuevas muestras de señas (Modo Captura, `CaptureMode.tsx`) y reentrena el modelo LSTM (`train_lstm.py`). **Decisión de diseño del equipo, sin respaldo directo en un interesado oficial del Registro de Interesados**: el Registro no lista un rol de usuario final equivalente. El trabajo de construcción de dataset y entrenamiento aparece en el EDT oficial como tareas del propio equipo del proyecto (paquetes 3.2.2 a 3.2.5, 5.2.1, 5.2.2), no como un rol operativo del producto entregado al Sanatorio. Se mantiene como actor de sistema — en vez de tratarse como trabajo puramente externo al software — porque el software realmente expone un Modo Captura en producción; el nombre se alinea con el rol oficial más cercano que aparece en la matriz de requisitos (columna "Validación", RF-05/RF-06/RNF-01/RNF-02/RNF-06: "Arnedo Emmanuel — Dev IA") y con el EDT ("Equipo de Proyecto"). |

No se modelan actores de sistema secundarios (LLM/Ollama, Piper TTS) porque
son componentes invocados sincrónicamente por el backend (`app.py`), sin
iniciativa propia ni interacción directa con una persona — no cumplen la
definición de actor de Larman/UML 2.5. Se documentan como dependencias
tecnológicas en la ERS (secciones 2.4 y 3.4).

No se modela un actor nuevo para el consumo de las métricas de auditoría del
RF-04 oficial (logs de uso y métricas operativas). El registro es una
subfunción automática, incluida por CU-01 y CU-04 (ver CU-11), sin
interacción humana directa en el software; su consumo (lectura/exportación
de esas métricas) es, por ahora, un proceso organizacional fuera de la
interfaz — corresponde al entregable de gestión E08 "Informe de Impacto
Operativo" (EDT) — y no una pantalla del sistema. El interesado oficial que
en la matriz de requisitos figura como dueño de RF-04 (**Dirección del
Sanatorio**) es, en consecuencia, un interesado de reporte, no un actor de
sistema: es la opción más limpia según Larman (evitar introducir un actor
sin interacción concreta con el sistema modelado) y evita inventar una
pantalla de administración fuera del alcance de TP2.

---

## 2. Casos de uso

| ID | Nombre | Actor principal | Nivel | Relación | Estado |
|----|--------|------------------|-------|----------|--------|
| CU-01 | Comunicarse mediante Lengua de Señas Argentina | Paciente | Objetivo de usuario | Base; incluye CU-02, CU-03 y CU-11; tiene como precondición CU-09 | Implementado |
| CU-02 | Traducir Secuencia de Señas a Oración Natural | Paciente (vía sistema) | Subfunción | Incluido por CU-01 | Implementado |
| CU-03 | Sintetizar Oración en Voz | Paciente (vía sistema) | Subfunción | Incluido por CU-01 | Implementado |
| CU-04 | Responder al Paciente | Personal de Recepción o Enfermería | Objetivo de usuario | Base; extendido por CU-05; incluye CU-11 | Implementado |
| CU-05 | Dictar Respuesta por Voz | Personal de Recepción o Enfermería | Subfunción | Extiende a CU-04 | Implementado |
| CU-06 | Capturar Muestra de Seña para Entrenamiento | Desarrollador de IA / Equipo de Proyecto | Objetivo de usuario | Base; incluye CU-07 | Implementado |
| CU-07 | Gestionar Vocabulario de Señas | Desarrollador de IA / Equipo de Proyecto | Subfunción | Incluido por CU-06 | Implementado |
| CU-08 | Entrenar el Modelo de Reconocimiento | Desarrollador de IA / Equipo de Proyecto | Objetivo de usuario | Independiente (precondición: CU-06 ejecutado antes) | Implementado |
| CU-09 | Otorgar Consentimiento Explícito de Cámara | Paciente | Objetivo de usuario | Precondición obligatoria de CU-01 | **Diseñado — pendiente de implementación** (RF-03 oficial) |
| CU-10 | Reportar Traducción Incorrecta o Ambigua | Paciente, Personal de Recepción o Enfermería | Objetivo de usuario | Extiende a CU-01 y a CU-04 (punto de extensión: "revisión de mensaje") | **Diseñado — pendiente de implementación** (RF-06 oficial) |
| CU-11 | Registrar Evento de Auditoría | (subfunción interna del sistema, sin actor humano) | Subfunción | Incluido por CU-01 y CU-04 | **Diseñado — pendiente de implementación** (RF-04 oficial) |

Paquetes del diagrama de casos de uso: **Comunicación** (CU-01 a CU-05,
CU-09, CU-10), **Gestión del Modelo** (CU-06 a CU-08), **Auditoría** (CU-11).
El diagrama de casos de uso (Entregable 02) usa una única columna dentro del
límite del sistema, o dos si once casos de uso no entran en una columna
legible (ver formato de referencia de cátedra).

---

## 3. Requisitos funcionales

### 3.1 Matriz oficial (texto literal — fuente: `LSA_Matriz de trazabilidad de Requisitos_V3.xlsx`)

Estos seis IDs están **reservados** para el texto oficial; no se reescriben.

| ID oficial | Descripción (texto literal) | Criterio de aceptación | Objetivo relacionado | Estado en LSA Salud |
|---|---|---|---|---|
| RF-01 | El sistema debe traducir LSA a texto y voz en tiempo casi real. | CRIT-01 | OE01 | Implementado (ver RF-01.1 a RF-01.7) |
| RF-02 | El sistema debe transcribir la voz o texto del profesional a un formato de texto accesible para el paciente sordo. | CRIT-03 | OE09 | Implementado (ver RF-02.1, RF-02.2) |
| RF-03 | La interfaz debe desplegar una pantalla de consentimiento explícito obligatorio antes de activar la cámara. | CRIT-07 | OE10 | **Diseñado — pendiente de implementación** (ver CU-09, RF-03.1) |
| RF-04 | El sistema debe registrar logs de uso internos y métricas operativas anónimas para auditoría. | CRIT-03 | OE08 | **Diseñado — pendiente de implementación** (ver CU-11, RF-04.1) |
| RF-05 | El sistema debe detectar cuando una seña no pueda interpretarse con confianza y evitar mostrar una traducción incorrecta. | CRIT-02/03 | OE06 | Implementado (mecanismo de umbral, ver RF-01.3, RF-01.4) |
| RF-06 | El sistema debe permitir que paciente o profesional reporten una traducción incorrecta/ambigua/no comprendida, para registrar el caso y mejorar el modelo. | CRIT-02/03 | OE06 | **Diseñado — pendiente de implementación** (ver CU-10, RF-06.1) |

### 3.2 Sub-requisitos técnicos trazables (implementados)

Cada uno es una realización parcial de su RF oficial padre (relación
muchos-a-uno). Continúan la numeración `RF-<oficial>.<n>`.

| ID | Texto (una línea) | CU relacionados | Traza a RF oficial |
|----|--------------------|------------------|---------------------|
| RF-01.1 | Captura de landmarks corporales en tiempo real desde la cámara (MediaPipe Holistic o MediaPipe Tasks). | CU-01 | RF-01 |
| RF-01.2 | Envío de los frames acumulados al backend para predicción vía WebSocket (JSON v1 o binario v2). | CU-01 | RF-01 |
| RF-01.3 | Clasificación de la seña mediante el modelo LSTM sobre una ventana de 45 frames, con umbral de confianza del 70 %. | CU-01, CU-02 | RF-01 (mecanismo de umbral realiza también RF-05 oficial) |
| RF-01.4 | Construcción incremental de la secuencia de palabras y detección de cierre de oración por inactividad (idle ≥ 800 ms + quietud de movimiento); descarta señas de baja confianza o de reposo. | CU-01 | RF-01 (realiza también RF-05 oficial) |
| RF-01.5 | Traducción de la secuencia de palabras a una oración natural en español (plantilla médica → caché → modelo de lenguaje local). | CU-02 | RF-01 |
| RF-01.6 | Síntesis de voz de la oración traducida con acento argentino y reproducción tras una ventana de exhibición previa. | CU-03 | RF-01 |
| RF-01.7 | Publicación del mensaje traducido en la conversación sincronizada entre estaciones (BroadcastChannel). | CU-01, CU-04 | RF-01 (soporta también RF-02 oficial, como canal de entrega) |
| RF-02.1 | Redacción y envío de una respuesta de texto por parte del personal de recepción o enfermería. | CU-04 | RF-02 |
| RF-02.2 | Dictado de la respuesta por voz (Web Speech API, es-AR), acumulable sobre texto ya escrito. | CU-05 | RF-02 |

### 3.3 Requisitos técnicos sin RF oficial directo (decisión de diseño del equipo)

Sin contraparte en la matriz oficial: sostienen CU-06/07/08 (gestión del
modelo), una decisión de arquitectura del equipo documentada y justificada
en ACT-03 (sección 1) y en el Entregable 02.

| ID | Texto (una línea) | CU relacionados |
|----|--------------------|------------------|
| RF-T-01 | Selección de una etiqueta de seña existente o creación de una etiqueta nueva antes de grabar una muestra. | CU-07 |
| RF-T-02 | Consulta de las clases reconocidas por el modelo y de las estadísticas de muestras por etiqueta del dataset activo. | CU-07 |
| RF-T-03 | Grabación de una o varias muestras de entrenamiento (45 frames) con cuenta regresiva y repeticiones configurables. | CU-06 |
| RF-T-04 | Persistencia de cada muestra grabada como archivo `.npy`, separando el árbol de captura legado del de MediaPipe Tasks (con blendshapes). | CU-06 |
| RF-T-05 | Reentrenamiento offline del modelo LSTM a partir de las muestras capturadas, con separación entrenamiento/validación y guardado del mejor modelo. | CU-08 |
| RF-T-06 | Selección de la estación de trabajo (Paciente / Recepción) desde la página de inicio. | Precondición de CU-01 y CU-04 |

### 3.4 Requisitos diseñados — pendientes de implementación

Cubren RF-03, RF-04 y RF-06 oficiales (decisión vinculante: deben quedar
diseñados a nivel de conceptos de dominio, casos de uso, mockups,
colaboración, arquitectura y modelo de datos, aunque el código actual no los
implemente).

| ID | Texto (una línea) | CU relacionados | Traza a RF oficial | Estado |
|----|--------------------|------------------|---------------------|--------|
| RF-03.1 | Antes de activar la cámara, el sistema debe desplegar una pantalla de consentimiento explícito y bloquear el acceso a la cámara hasta que el paciente lo otorgue. | CU-09 | RF-03 | Diseñado — pendiente de implementación |
| RF-04.1 | El sistema debe registrar, de forma automática y anónima, un evento de auditoría por cada operación de sistema relevante (predicción, traducción, síntesis, respuesta, captura), sin datos identificatorios ni imágenes/video. | CU-11 | RF-04 | Diseñado — pendiente de implementación |
| RF-06.1 | El paciente o el personal de recepción/enfermería deben poder marcar un mensaje de la conversación como traducción incorrecta o ambigua, indicando un motivo, para registrar el caso. | CU-10 | RF-06 | Diseñado — pendiente de implementación |

Total: **9 RF sub-requisitos implementados** (RF-01.1–RF-01.7, RF-02.1–RF-02.2),
**6 RF técnicos sin RF oficial** (RF-T-01–RF-T-06), **3 RF diseñados
pendientes** (RF-03.1, RF-04.1, RF-06.1).

---

## 4. Requisitos no funcionales

### 4.1 Matriz oficial (texto literal)

| ID oficial | Descripción (texto literal) | Criterio de aceptación | Estado en LSA Salud |
|---|---|---|---|
| RNF-01 | Latencia: procesamiento e interpretación de señas en tiempo real <1 segundo. | CRIT-01 | Parcial — objetivo de diseño, sin medición formal registrada (ver RNF-01.1) |
| RNF-02 | Precisión: accuracy mínimo 90% en entornos clínicos controlados. | CRIT-02 | Parcial — no verificado formalmente (ver RNF-02.1) |
| RNF-03 | Seguridad y Privacidad: 100% de interacciones de video procesadas sin almacenamiento persistente de imágenes/video. | CRIT-04 | Implementado (ver RNF-03.1) |
| RNF-04 | Compatibilidad de Hardware: exclusivamente cámaras, pantallas doble cara y componentes comerciales estándar. | CRIT-06 | Parcial (ver RNF-04.1) |
| RNF-05 | Especialización de Datos: dataset ampliado y adaptado al dominio clínico (síntomas, triaje, dolor). | CRIT-02/05 | Parcial (ver RNF-05.1) |
| RNF-06 | El dataset clínico LSA debe ser revisado y validado lingüísticamente por intérpretes oficiales antes de usarse como base final. | CRIT-05 | Pendiente — proceso organizacional (ver RNF-06.1) |
| RNF-07 | El sistema debe poder usarse en una estación fija de guardia/triaje con cámara, pantalla doble cara, micrófono y altavoces. | CRIT-06 | Parcial (ver RNF-07.1) |

### 4.2 Sub-requisitos técnicos trazables

| ID | Atributo | Texto (una línea) | Traza a RNF oficial | Estado |
|----|----------|--------------------|----------------------|--------|
| RNF-01.1 | Rendimiento | Metas de latencia extremo a extremo expresadas en p50/p95 (ver ERS 3.3): p50 ≤ 600 ms (ruta con plantilla), p95 ≤ 1 s (caso general). | RNF-01 | Objetivo de diseño, no medición formal registrada |
| RNF-02.1 | Precisión del modelo | Exactitud de validación del modelo LSTM (`ModeloDeReconocimiento.exactitudDeValidación`, ver Entregable 01), calculada durante `train_lstm.py` sobre el 20% de validación. | RNF-02 | No hay un harness formal que valide 90% como criterio de aceptación automatizado; recomendado como parte de E05 (Informe de Pruebas Controladas) |
| RNF-03.1 | Seguridad / privacidad | Todo el procesamiento y almacenamiento ocurre en la máquina local; no hay persistencia de conversaciones (estado en memoria + BroadcastChannel); los eventos de auditoría (RF-04.1) se diseñan sin imágenes ni video, consistentes con esta restricción. | RNF-03 | Implementado |
| RNF-04.1 / RNF-07.1 | Compatibilidad de hardware / estación fija | Las dos estaciones sincronizadas (Paciente y Recepción), sobre el mismo navegador y canal BroadcastChannel, con doble monitor, **implementan las dos caras de la estación fija de guardia/triaje** exigida por RNF-04/RNF-07 oficiales: cámara y pantalla del lado del paciente, pantalla y controles del lado del personal. El **ensamblaje físico** de esas dos pantallas y la cámara sobre hardware comercial (mostrador o box existente) es tarea del entregable E07 "Estación Desplegada en Guardia" (EDT), fuera del alcance de software de TP2. | RNF-04, RNF-07 | Parcial — diseño de software completo; integración física pendiente (E07) |
| RNF-05.1 | Especialización de datos | El Modo Captura y los árboles `dataset/custom`, `dataset/custom_tasks`, `dataset/custom_blendshapes` permiten ampliar el vocabulario a señas médicas (dolor, cabeza, respirar, etc.); la cobertura completa del dominio clínico (síntomas, triaje) y su validación no están verificadas al día de este documento. | RNF-05 | Parcial |
| RNF-06.1 | Validación lingüística | La validación del dataset clínico por intérpretes oficiales de LSA es un proceso organizacional (EDT, paquete 3.2.5), no una función de software; el riesgo #1 del Registro de Riesgos ("falta de disponibilidad de intérpretes oficiales", calificación *Inaceptable*, 30%) aplica directamente a este requisito. | RNF-06 | Pendiente — proceso organizacional, no verificable en código |

### 4.3 Requisitos técnicos sin RNF oficial directo

| ID | Atributo | Texto (una línea) |
|----|----------|--------------------|
| RNF-T-01 | Fiabilidad | El WebSocket de predicción se reconecta automáticamente cada 2 s; si el LLM local falla se usa el texto original; si Piper TTS no está disponible se omite el audio sin interrumpir el flujo. |
| RNF-T-02 | Disponibilidad | El sistema opera de forma autónoma en una PC local; el pipeline de reconocimiento y síntesis no requiere conectividad externa (Ollama y Piper corren localmente). |
| RNF-T-03 | Mantenibilidad | Responsabilidades separadas en hooks de React por función (cámara, WebSocket, chat, voz, construcción de oración) y modelo LSTM desacoplado del backend en un módulo propio. |
| RNF-T-04 | Portabilidad | Backend en Python 3.9+/FastAPI y frontend en Next.js 14/TypeScript, ambos multiplataforma; probado en Windows. |
| RNF-T-05 | Usabilidad / accesibilidad | Conversación fluida sin botones de confirmación manual (la ventana de exhibición previa a la voz actúa como confirmación automática); indicadores visuales de estado (en vivo, grabando, cuenta regresiva). |

---

## 5. Objetivos específicos (OE) y criterios de aceptación (CRIT) — anexo de trazabilidad

Fuente: TP1 (Acta de Constitución) y TP2 (Declaración de Alcance), citados
en `docs/referencias/RESUMEN_REFERENCIAS.md`, secciones 1 y 2.

| OE | Meta cuantificada | RF/RNF oficiales relacionados | CRIT relacionado |
|---|---|---|---|
| OE01 | -80% tiempo de interacción (4 min → <1 min), primeros 6 meses | RF-01 | CRIT-01 |
| OE02 | -50% de la brecha de permanencia en urgencias, 1er año | RF-01, RF-02 | CRIT-01, CRIT-03 |
| OE03 | Recuperar ≥150 hs operativas/año, 1er año | RNF-04, RNF-07 | CRIT-06 |
| OE04 | Comprensión clínica del paciente 18% → >90%, 12 meses | RNF-05, RNF-06 | CRIT-02, CRIT-05 |
| OE05 | Readmisión a 30 días 24,3% → <15%, 24 meses | RF-01, RF-02 | — |
| OE06 | Precisión del reconocimiento ≥90% (controlado) / ≥85% (real) | RF-05, RF-06, RNF-02 | CRIT-02, CRIT-03 |
| OE07 | Latencia de interpretación <1 segundo | RNF-01 | CRIT-01 |
| OE08 | Adopción por ≥70% del personal de recepción/triaje, 6 meses | RF-04 | CRIT-03 |
| OE09 | Satisfacción del paciente >85% | RF-02 | — |
| OE10 | 100% de interacciones sin almacenamiento persistente | RF-03, RNF-03 | CRIT-04, CRIT-07 |

| CRIT | Criterio de aceptación (TP2) |
|---|---|
| CRIT-01 | Latencia percibida <1 s en condiciones normales |
| CRIT-02 | Accuracy ≥90% en reconocimiento en entornos controlados |
| CRIT-03 | Precisión ≥85% en pruebas operativas reales de guardia |
| CRIT-04 | 100% de interacciones de video procesadas sin almacenamiento persistente |
| CRIT-05 | Dataset clínico ampliado con aval formal de la comunidad de intérpretes LSA |
| CRIT-06 | Estaciones con componentes estándar de mercado, sin hardware médico especializado |
| CRIT-07 | Pantalla de consentimiento obligatoria (citado en la matriz de requisitos junto a RF-03; no listado en la tabla CRIT-01..06 de TP2 — inconsistencia menor entre documentos oficiales, documentada aquí) |

---

## 6. Conceptos del dominio (Modelo de Dominio)

| Concepto | Descripción breve |
|----------|--------------------|
| Paciente | Persona sorda/hipoacúsica que se comunica mediante LSA. |
| Personal de Recepción o Enfermería | Personal que atiende y responde al paciente. |
| Desarrollador de IA / Equipo de Proyecto | Personal técnico que amplía el vocabulario y reentrena el modelo. |
| EstaciónDeAtención | Pantalla/estación (Paciente o Recepción) sincronizada con la otra; sus dos caras físicas conforman la estación fija de guardia/triaje (RNF-04/07 oficiales). |
| Conversación | Intercambio de mensajes de una sesión de atención. |
| Mensaje | Unidad de comunicación enviada por el paciente o el personal de recepción/enfermería. |
| SecuenciaDeSeñas | Secuencia de palabras reconocidas en curso, antes de traducirse. |
| ClaseDeSeña | Categoría de seña reconocible por el modelo (p. ej. "dolor"). |
| PalabraReconocida | Ocurrencia de una clase de seña detectada durante una secuencia, con su confianza. |
| Traducción | Resultado de convertir una secuencia de señas en una oración en español. |
| PlantillaMédica | Frase médica predefinida asociada a una combinación conocida de señas. |
| SíntesisDeVoz | Locución sonora asociada a un mensaje traducido. |
| ModeloDeReconocimiento | Red LSTM entrenada capaz de clasificar clases de seña. |
| MuestraDeEntrenamiento | Grabación de una seña capturada para (re)entrenar el modelo. |
| ConsentimientoDeCámara | Autorización explícita del paciente para activar la cámara, otorgada antes de iniciar CU-01 (RF-03 oficial). |
| EventoDeAuditoría | Registro anónimo de una operación de sistema relevante, sin datos identificatorios ni imágenes/video (RF-04 oficial). |
| ReporteDeTraducción | Señalamiento de un mensaje como traducción incorrecta o ambigua, con motivo, hecho por el paciente o el personal (RF-06 oficial). |

Diagramas de clases (dos vistas): `docs/diagramas/dominio/gen_modelo_dominio.py` → `docs/img/01_modelo_dominio_a.pdf` y `01_modelo_dominio_b.pdf`.
Diagrama de casos de uso: `docs/diagramas/02_casos_uso.puml` → `docs/img/02_casos_uso.pdf`.

---

## 7. Pantallas (mockups, Entregable 04)

| ID | Pantalla | Ruta | Componentes reales representados | Estado |
|----|----------|------|-----------------------------------|--------|
| P-01 | Selección de Estación | `/` | `web/app/page.tsx` | Implementado |
| P-02 | Estación del Paciente (modo predicción) | `/paciente` | `web/app/paciente/page.tsx`, `Header`, `TopPredictions`, `ChatBubble` | Implementado (con elemento de reporte diseñado, pendiente) |
| P-03 | Estación de Recepción | `/recepcion` | `web/app/recepcion/page.tsx`, `Header`, `ChatBubble`, `ReceptionControls` | Implementado (con elemento de reporte diseñado, pendiente) |
| P-04 | Modo Captura | `/paciente` (`mode === "capture"`) | `web/components/capture/CaptureMode.tsx` | Implementado |
| P-05 | Pantalla de Consentimiento | `/paciente` (previa a activar la cámara) | Diseño nuevo — sin componente real todavía | **Diseñado — pendiente de implementación** |

Cada elemento anotado dentro de una pantalla usa un callout numerado en
círculo (①②③…), único por pantalla (no se reinicia entre secciones de la
misma pantalla). El Entregable 07 referencia estos callouts como
"panel ③ de la Pantalla P-02".

## 8. Operaciones de sistema y diagramas de colaboración (Entregable 08)

| ID | Operación de sistema | CU realizado | Diagrama de colaboración | Estado |
|----|------------------------|--------------|---------------------------|--------|
| SO-01 | `reconocerSeña(frame)` | CU-01 (captura → buffer → predicción) | DC-01 | Implementado |
| SO-02 | `cerrarOracionYTraducir(secuencia)` | CU-01 / CU-02 (cierre de oración y traducción) | DC-02 | Implementado |
| SO-03 | `sintetizarVoz(oracion)` | CU-03 | DC-03 | Implementado |
| SO-04 | `enviarRespuesta(mensaje)` | CU-04 (sincronización por BroadcastChannel) | DC-04 | Implementado |
| SO-05 | `capturarMuestra(frames, etiqueta)` | CU-06 | DC-05 | Implementado |
| SO-06 | `otorgarConsentimiento(paciente)` | CU-09 | DC-06 | Diseñado — pendiente de implementación |
| SO-07 | `registrarEventoAuditoria(operacion)` | CU-11 | DC-07 | Diseñado — pendiente de implementación |
| SO-08 | `reportarTraduccion(mensaje, motivo)` | CU-10 | DC-08 | Diseñado — pendiente de implementación |

Diagramas: `docs/diagramas/colaboracion/08_colaboracion_dc0N.drawio` → `docs/img/08_colaboracion_dc0N.pdf`.
