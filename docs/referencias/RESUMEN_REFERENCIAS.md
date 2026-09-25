# Resumen de documentos de referencia — LSA Salud (UTN-FRT, Grupo 9)

> Compilado a partir de los documentos oficiales de la cátedra Proyecto (UTN-FRT) en
> `docs/referencias/`. Estos documentos son la fuente de gobierno del proyecto; los
> entregables técnicos generados en `docs/` (Fase 1: Modelo de Dominio, Casos de Uso,
> ERS, `docs/IDS.md`) deben alinearse a ellos, no al revés.

---

## 1. Identidad del proyecto

| Campo | Valor |
|---|---|
| Nombre oficial | **LSA Salud** (título largo en TP0: "Traductor LSA Salud") |
| Nombre interno del repositorio | "Nexora" — **no aparece en ningún documento oficial**; es un alias técnico del código, no el nombre del proyecto académico. |
| ID de proyecto | `LSASALUD-G9` (también `LSASALU D-G9` / `LSASALUD_G9` según el documento — inconsistencia menor de formato entre TP2/EDT) |
| Cliente | Sanatorio 9 de Julio (San Miguel de Tucumán) |
| Patrocinador (sponsor) | Sanatorio 9 de Julio / Cátedra Proyecto UTN-FRT |
| Director de Proyecto | Santino Hamada |
| Tutor | Vicente, Francisco José |
| Cotutor | Emmanuel López |
| Cátedra / Institución | PROYECTO — Departamento de Sistemas, Facultad Regional Tucumán (UTN-FRT) |
| Equipo (Ingeniería en Sistemas, UTN-FRT) | Santino Hamada (Director; frontend/backend); García Tarcic Iñaki Ezequiel (Analista funcional; backend/QA-fullstack); Veliz Héctor Matías (QA y Testing; frontend); Arnedo Emmanuel Augusto (Desarrollador IA; QA-fullstack) |
| Fechas clave | Solicitud de tema: 27/04/2026 · Acta de Constitución: 01/05/2026 · Declaración de Alcance: 16/05/2026 · EDT: 09/06/2026 · Ejecución del proyecto (estimación financiera): 12/05/2026 → 17/12/2026 · Defensa final de tesis: 15/11/2026 (fecha límite improrrogable, TP2) |
| Códigos de documento vistos | TP2 = `T045`; Registro de Riesgos = `RR02` |
| Convención de versionado | Sufijos `V.3`, `V2`, `V1`; EDT usa "Edición 1.2" por paquete de trabajo |
| Convención de encabezado | Todo documento formal lleva bloque: ID DE PROYECTO / NOMBRE PROYECTO / CLIENTE / PREPARADO POR (o PATROCINADOR) / FECHA / CÓDIGO DE DOCUMENTO |
| `formato Diag caso de uso.jpeg` | Plantilla/ejemplo de formato UML de diagrama de casos de uso (no se modela contenido, solo referencia de formato) |

---

## 2. Objetivos, alcance, entregables, supuestos, restricciones

**Problema (TP0/TP1):** ausencia de mediación comunicacional para pacientes sordos/hipoacúsicos
usuarios de LSA en recepción, admisión, triaje y guardia. Evidencia citada: +30 min de estancia en
urgencias vs. oyentes; 57% identifica la comunicación como principal barrera; en Tucumán ~60% de
consultas de guardia son triaje verde/azul (interacciones breves y estructuradas, ideales para
automatizar).

**Objetivo general:** desarrollar e implementar un sistema de IA/visión por computadora que facilite
la comunicación LSA↔personal de salud en entornos de atención médica.

**Objetivos específicos (OE01–OE10, TP1)** — no están en nuestros documentos actuales, son metas
cuantificadas:
- OE01: -80% tiempo de interacción (4 min → <1 min), primeros 6 meses.
- OE02: -50% de la brecha de permanencia en urgencias (hoy +30 min vs. oyentes), 1er año.
- OE03: recuperar ≥150 hs operativas/año (base 50.000 consultas/año), 1er año.
- OE04: comprensión clínica del paciente 18% → >90%, 12 meses.
- OE05: readmisión a 30 días 24,3% → <15%, 24 meses.
- OE06: precisión del reconocimiento ≥90% (controlado) / ≥85% (real), fase piloto + 6 meses.
- OE07: latencia de interpretación <1 segundo.
- OE08: adopción por ≥70% del personal de recepción/triaje, 6 meses.
- OE09: satisfacción del paciente >85%.
- OE10: 100% de interacciones sin almacenamiento persistente de imágenes/datos sensibles.

**Alcance del producto (TP2):** sistema bidireccional LSA↔español en **estaciones fijas** con
pantalla de doble cara, cámara estándar, micrófono y altavoces; dataset clínico ampliado desde
LSA64; arquitectura *privacy by design* (sin almacenamiento persistente de video/imágenes,
consentimiento explícito); integración física no invasiva (mostradores/boxes existentes).

**Alcance del proyecto (fases, TP2):** Relevamiento → Diseño → Construcción del Dataset →
Desarrollo/Entrenamiento (MVP) → Pruebas e Implementación Piloto → Evaluación y Cierre.

**Exclusiones (TP2):**
- Capacitación general en LSA al personal del sanatorio.
- Desarrollo de hardware a medida (solo ensamblaje de hardware comercial).
- Integración con la Historia Clínica Electrónica (HCE) core.
- Interpretación de modismos regionales complejos (1ª versión).
- Mantenimiento técnico post-entrega (posterior al 15/11/2026).
- Reestructuración de redes/cableado del sanatorio.

**Supuestos (TP2):** disponibilidad de instalaciones del sanatorio; colaboración activa y constante
de intérpretes LSA externos; estabilidad eléctrica/red; disponibilidad de hardware comercial en el
mercado local; disposición del personal de guardia para entrevistas y uso del piloto.

**Restricciones (TP2):** fecha límite improrrogable 15/11/2026; hardware exclusivamente comercial de
bajo costo; cumplimiento estricto de normativa de protección de datos (0% almacenamiento
persistente); todo el trabajo de campo dentro del Sanatorio 9 de Julio (San Miguel de Tucumán);
equipo limitado a los 4 integrantes UTN-FRT (sin tercerizar desarrollo).

**Criterios de aceptación del producto (TP2):**
| ID | Criterio |
|---|---|
| CRIT-01 | Latencia percibida <1 s en condiciones normales |
| CRIT-02 | Accuracy ≥90% en reconocimiento en entornos controlados |
| CRIT-03 | Precisión ≥85% en pruebas operativas reales de guardia |
| CRIT-04 | 100% de interacciones de video procesadas sin almacenamiento persistente |
| CRIT-05 | Dataset clínico ampliado con aval formal de la comunidad de intérpretes LSA |
| CRIT-06 | Estaciones con componentes estándar de mercado, sin hardware médico especializado |

**Entregables del proyecto (TP2, E01–E10):**
| ID | Entregable | Fecha | Responsable |
|---|---|---|---|
| E01 | Documento de Alcance Validado | 30/05/2026 | Veliz |
| E02 | Documento de Arquitectura | 15/06/2026 | Arnedo |
| E03 | Dataset Clínico LSA | 30/06/2026 | Equipo |
| E04 | Producto Mínimo Viable (MVP) | 30/07/2026 | Equipo |
| E05 | Informe de Pruebas Controladas | 15/08/2026 | Veliz |
| E06 | Modelo de IA Optimizado | 01/09/2026 | Arnedo |
| E07 | Estación Desplegada en Guardia | 15/09/2026 | Hamada |
| E08 | Informe de Impacto Operativo | 15/10/2026 | García Tarcic |
| E09 | Sistema Final y Manuales | 01/11/2026 | Equipo |
| E10 | Informe Final de Tesis | 15/11/2026 | Equipo |

---

## 3. Requisitos — Matriz de trazabilidad (`LSA_Matriz de trazabilidad de Requisitos_V3.xlsx`)

**Esta es la matriz OFICIAL y completa — solo 6 RF y 7 RNF**, muy distinta en número y contenido de
los RF-01..15 / RNF-01..07 de `docs/IDS.md` (ver GAP ANALYSIS, sección 8).

| ID | Descripción | Criterio de aceptación | Interesado dueño | Entregable | Prioridad | Validación | Objetivo relacionado |
|---|---|---|---|---|---|---|---|
| RF-01 | El sistema debe traducir LSA a texto y voz en español en tiempo casi real. | CRIT-01 (latencia <1s) | Pacientes sordos/hipoacúsicos y Personal administrativo/médico | E04 (MVP) | Alto | Santino Hamada (Director) | OE01 |
| RF-02 | El sistema debe transcribir la voz o texto del profesional a un formato de texto accesible para el paciente sordo. | CRIT-03 (precisión ≥85% real) | Personal médico y administrativo de guardia | E09 (Sistema Final) | Alto | García Tarcic Iñaki (Analista Funcional) | OE09 |
| RF-03 | La interfaz debe desplegar una pantalla de consentimiento explícito obligatorio antes de activar la cámara. | CRIT-07* (pantalla de consentimiento obligatoria) | Comité de Ética del Sanatorio y Pacientes usuarios de LSA | E04 (MVP) | Alto | Veliz Héctor Matías (QA) | OE10 |
| RF-04 | El sistema debe registrar logs de uso internos y métricas operativas anónimas para auditoría. | CRIT-03 (correcta generación de métricas) | Dirección del Sanatorio y Equipo de Proyecto UTN | E08 (Impacto Operativo) | Medio | García Tarcic Iñaki (Analista Funcional) | OE08 |
| RF-05 | El sistema debe detectar cuando una seña no pueda interpretarse con confianza y evitar mostrar una traducción incorrecta. | CRIT-02/03 (falsos positivos / precisión) | Pacientes usuarios de LSA y Personal médico de guardia | E06 (Modelo de IA Optimizado) | Alto | Veliz Héctor Matías (QA) | OE06 |
| RF-06 | El sistema debe permitir que paciente o profesional reporten una traducción incorrecta/ambigua/no comprendida, para registrar el caso y mejorar el modelo. | CRIT-02/03 | Pacientes usuarios de LSA y Personal médico de guardia | E06 (Modelo de IA Optimizado) | Alto | Veliz Héctor Matías (QA) | OE06 |
| RNF-01 | Latencia: procesamiento e interpretación de señas en tiempo real <1 segundo. | CRIT-01 | Personal médico y administrativo de guardia | E06 | Alto | Arnedo Emmanuel (Dev IA) | OE07 |
| RNF-02 | Precisión: accuracy mínimo 90% en entornos clínicos controlados. | CRIT-02 | Equipo de Proyecto UTN y Comunidad de intérpretes LSA | E05 | Alto | Arnedo Emmanuel (Dev IA) | OE06 |
| RNF-03 | Seguridad y Privacidad: 100% de interacciones de video procesadas sin almacenamiento persistente de imágenes/video. | CRIT-04 | Sanatorio (Asesoría Legal) y Pacientes sordos | E09 | Alto | Veliz Héctor Matías (QA) | OE10 |
| RNF-04 | Compatibilidad de Hardware: exclusivamente cámaras, pantallas doble cara y componentes comerciales estándar. | CRIT-06 | Dirección del Sanatorio (Infraestructura) | E07 | Alto | Santino Hamada (Director) | OE03 |
| RNF-05 | Especialización de Datos: dataset ampliado y adaptado al dominio clínico (síntomas, triaje, dolor). | CRIT-02/05 | Personal de enfermería de triage e Intérpretes de LSA | E03 | Alto | Equipo + Intérpretes de LSA | OE04 |
| RNF-06 | El dataset clínico LSA debe ser revisado y validado lingüísticamente por intérpretes oficiales antes de usarse como base final. | CRIT-05 | Intérpretes de LSA | E03 | Alto | Arnedo Emmanuel (Dev IA) | OE04 |
| RNF-07 | El sistema debe poder usarse en una estación fija de guardia/triaje con cámara, pantalla doble cara, micrófono y altavoces. | CRIT-06 | Dirección del Sanatorio y Personal administrativo/médico | E07 | Alto | Santino Hamada (Director) | OE03 |

\* CRIT-07 se menciona en la matriz pero no figura en la lista CRIT-01..06 de TP2 (posible criterio
agregado en la matriz sin sincronizar con TP2 — inconsistencia menor entre documentos oficiales).

**Requisitos/criterios adicionales mencionados en TP0/TP1/TP2 pero fuera de la matriz:** los OE01–OE10
(objetivos específicos, sección 2) y CRIT-01..06 (criterios de aceptación, sección 2) funcionan como
requisitos de facto (metas medibles) aunque no tengan ID de tipo RF/RNF.

---

## 4. Interesados (`LSA-Salud_Registro de Interesados_V1 (1).xlsx`)

**Hoja "Registro de Interesados"** (completa):

| Nombre / Rol | Puesto | Rol en el proyecto | Expectativas principales | Requisitos involucrados | Interno/Externo | Tipo (defensor/crítico/neutral/latente) | Estrategia de gestión |
|---|---|---|---|---|---|---|---|
| Francisco Vicente | - | Tutor | Sistema robusto; alta precisión del traductor | Traducción LSA→texto; reconocimiento de voz | Externo | Defensor/Crítico | Gestionar de Cerca |
| Emmanuel López | - | Cotutor | (sin datos) | Traducción LSA→texto; reconocimiento de voz | Externo | Defensor/Crítico | Gestionar de Cerca |
| Sanatorio 9 de Julio | - | Cliente | Mejorar comunicación y eficiencia de guardia | Traducción LSA→texto; reconocimiento de voz | Interno | Crítico | Gestionar de Cerca |
| Estado (Ley 27.710) | - | Marco Legal | — | Traducción LSA→texto; reconocimiento de voz | Externo | Neutral | Mantener Satisfecho |
| Recepcionista | - | Usuario | Usar el traductor para comunicación directa y privada con el paciente | Traducción LSA→texto | Interno | Crítico | Gestionar de Cerca |
| Personas que se comunican con LSA | - | Usuario | Comunicación directa y privada con el personal | Traducción LSA→texto | Externo | Crítico | Gestionar de Cerca |
| Enfermero/a | - | Usuario | Comunicación directa y privada con el paciente | Traducción LSA→texto | Interno | Crítico | Gestionar de Cerca |
| Natalia García Escudé | - | Doctora que aporta información | Que el grupo ponga en práctica el proyecto pronto | — | Externo | Defensor | Mantener Informado |
| Competencia | - | - | Que el producto no supere al suyo | — | Externo | Latente | - |
| Facundo Quiroga, Pedro Dal Bianco, Gastón Ríos, Franco Ronchetti, Oscar Stanchi, Waldo Hasperupe, Alejandro Rosete | - | Creadores de dataset público de LSA | — | Recopilación de datos para entrenar la IA | Externo | Neutral | Esfuerzo Mínimo |
| Mediapipe, Numpy, Pandas, Tensorflow, OpenCV | - | Framework/librería | — | Entrenamiento de la IA | Externo | Neutral | Esfuerzo Mínimo |

**Hoja "Matriz Poder-Interés":** confirma cuadrantes — *Gestionar de cerca* (alto poder/alto interés):
Francisco Vicente, Emmanuel López, Sanatorio 9 de Julio, Recepcionista, Enfermero/a, Personas que se
comunican con LSA. *Mantener Satisfecho* (alto poder/bajo interés): Estado, Competencia.
*Mantener Informado* (bajo poder/alto interés): Natalia García Escudé. *Esfuerzo Mínimo*: creadores
de datasets y librerías de código.

**Relevancia para casos de uso:** los interesados "Recepcionista" y "Enfermero/a" son roles
**separados** en el registro oficial, aunque ambos comparten el mismo requisito e interés. Nuestro
ACT-02 ya los generaliza correctamente como "Personal de recepción o enfermería" — coherente.
"Personas que se comunican con LSA" = ACT-01 Paciente — coherente. No hay ningún interesado oficial
equivalente a un "Administrador del Modelo" (ACT-03): el trabajo de dataset/entrenamiento aparece
como tarea del **equipo del proyecto**, no como un rol de usuario final del producto — ver gap #4.

---

## 5. EDT / WBS (`LSA_Estructura de Desglose de Trabajo_V3.pdf`, 37 págs.)

Paquetes de trabajo relevantes a los entregables de software (análisis/diseño/desarrollo):

| Ref. | Paquete | Responsable | Esfuerzo |
|---|---|---|---|
| 2.1.1 | Matriz de trazabilidad de requisitos | Hamada | 16 hs |
| 2.1.2 | Definición del alcance | Arnedo | 16 hs |
| 2.1.3 | EDT | García | 36 hs |
| 3.1.1 | Obtención de tecnologías | Hamada | 36 hs |
| 3.1.2 | Investigación de sistemas similares | García | 32 hs |
| 3.2.1 | Especificación de funcionalidades de LSA Salud | Arnedo | 28 hs |
| 3.2.2 | Análisis del Dataset y modelo de IA | Hamada | 28 hs |
| 3.2.3 | Análisis del módulo de texto a voz | Veliz | 18 hs |
| 3.2.4 | Dataset médico especializado | Arnedo | 60 hs |
| 3.2.5 | Validación lingüística con intérpretes de LSA | Arnedo | 48 hs |
| 4.1.1 | Diseño de la arquitectura del sistema | García | 28 hs |
| 4.1.2 | Diseño de endpoints | Arnedo | 20 hs |
| 4.1.3 | Flujo de datos | Hamada | 24 hs |
| 4.2.1 | Wireframes de las pantallas | García | 20 hs |
| 4.2.2 | Maquetación estética y estilos (Mockups) | Veliz | 18 hs |
| 5.1.1 / 5.1.2 | Frontend: estructura/maquetación + consumo de endpoints | Veliz / Arnedo | 208 + 28 hs |
| 5.2.1 / 5.2.2 | Preprocesamiento de datos + Entrenamiento/validación IA | García | 36 + 52 hs |
| 5.3.1 | Servidor API de interconexión | García | 36 hs |
| 5.4.1 / 5.4.2 / 5.4.3 | Pruebas E2E / hardware físico / validación con médicos | Veliz / Hamada / García | 28+28+32 hs |
| 5.5.1 / 5.5.2 | Guía de usuario + Informe final del sistema | Arnedo / Hamada | 16+20 hs |
| 6.1.1 / 6.1.2 | Contenedorización (Docker) + Scripts de automatización | Hamada / Arnedo | 18+12 hs |
| 6.2.1 | Pruebas de funcionamiento en entorno desconectado | Hamada | 22 hs |

**Nota clave de trazabilidad EDT↔Riesgos:** el registro de riesgos referencia estos mismos códigos
de paquete (`# WBS`), p. ej. riesgo #1 → 3.2.5 (validación lingüística), riesgo #4 → 6.2.1
(iluminación en boxes), riesgo #5 → 4.1.3 (latencia). Esto confirma que 3.2.1 "Especificación de
funcionalidades" (Fase de análisis, no en nuestros documentos actuales bajo ese nombre) es el paquete
que formalmente debía producir los RF/RNF — probablemente el origen directo de la matriz de
trazabilidad oficial.

---

## 6. Riesgos (`TP5_Registro_de_riesgos_LSA_V2.xls`) — top riesgos relevantes a requisitos/diseño

26 riesgos identificados (VME = Valor Monetario Esperado, todos en estado "Open"). Los de mayor
impacto/calificación "Inaceptable" y con relación directa a requisitos/arquitectura:

| # | WBS | Riesgo | Calificación | Prob. | VME |
|---|---|---|---|---|---|
| 1 | 3.2.5 | Falta de disponibilidad de intérpretes oficiales de LSA para validar dataset clínico | Inaceptable | 30% | 1.5 |
| 4 | 6.2.1 | Iluminación deficiente en boxes que impida captura de gestos | Inaceptable | 25% | 1.25 |
| 5 | 4.1.3 | Latencia de procesamiento de video IA superior al umbral de 1s (CRIT-01) | Inaceptable | 35% | 1.75 |
| 9 | 3.2.4 | Dificultad para compilar suficientes muestras de LSA para vocabulario médico específico | Inaceptable | 30% | 1.5 |
| 13 | 4.1.1 | Cambios en normativas de privacidad del sanatorio sobre captura de video | Inaceptable | 15% | 0.75 |
| 16 | 5.2.2 | Falla del modelo al capturar gestos faciales/no manuales vitales en la sintaxis de LSA | Inaceptable | 30% | 1.5 |
| 21 | 5.4.3 | Sanatorio revoca/posterga acceso a boxes de triaje para el piloto | Inaceptable | 20% | 1.0 |
| 2 | 5.2.2 | Sobreajuste (overfitting) del modelo Transformer limitando generalización de señas | Aceptable con atención | 40% | 1.6 |
| 6 | 5.2.1 | Ruido visual que afecte precisión de extracción de coordenadas (x,y,z) | Aceptable con atención | 60% | 2.4 |
| 24 | 5.4.1 | Latencias inmanejables entre frontend y modelo IA, requiere reescribir lógica de conexión | Inaceptable | 30% | 1.5 |

Ejemplos de mitigación documentada (planes de respuesta por riesgo): contacto temprano con
asociaciones de sordos para RF/RNF de validación lingüística (riesgo 1); data augmentation +
selección de cámaras con compensación de exposición para iluminación (riesgo 4).

---

## 7. Planificación financiera (`LSA_Planificación Financiera_V3.xls`)

Hojas: Estimación, Plan_Financiero, Indicadores, Situación, Evolución, Cierre. Contenido: costos de
personal por categoría/hora (1136 hs totales, $10.780.000 en personal), subcontratación de
intérpretes LSA (26 hs, $182.000), costos varios (equipo, internet, electricidad, cámara,
micrófono), precio de venta estimado $15.060.400, financiamiento vía FONCyT/PROINE/Premio INVAP.

**No contiene información adicional relevante para alcance o requisitos** más allá de lo ya cubierto
en TP1/TP2 (es exclusivamente presupuesto/cronograma de costos, sin nuevas reglas de negocio ni
restricciones funcionales).

---

## 8. GAP ANALYSIS vs. `docs/IDS.md` (y verificación breve en código)

Código revisado: `app.py`, `web/app/paciente/page.tsx`, `web/app/recepcion/page.tsx`,
`web/lib/mediapipe.ts`, `web/hooks/*.ts`.

### 8.1 Requisitos oficiales vs. estado de implementación

| ID oficial | Requisito | Estado | Evidencia |
|---|---|---|---|
| RF-01 | Traducir LSA a texto y voz en tiempo casi real | **IMPLEMENTADO** | Pipeline completo: captura MediaPipe → LSTM → traducción → Piper TTS (cubierto por RF-01..RF-06 de `IDS.md`) |
| RF-02 | Transcribir voz/texto del profesional a texto accesible para el paciente | **IMPLEMENTADO** | RF-08/RF-09 de `IDS.md`; `web/app/recepcion/page.tsx` (texto + dictado Web Speech API) |
| RF-03 | Pantalla de consentimiento explícito obligatorio antes de activar la cámara | **NO IMPLEMENTADO** | Sin coincidencias para "consent/consentimiento" en `web/app`, `web/components`, `web/hooks`; no existe en `IDS.md` |
| RF-04 | Logs de uso internos y métricas operativas anónimas para auditoría | **NO IMPLEMENTADO** | Sin `logging`/`audit` en `app.py`; RF-11 de `IDS.md` solo cubre estadísticas de dataset, no auditoría operativa |
| RF-05 | Detectar seña no interpretable con confianza y evitar traducción incorrecta | **IMPLEMENTADO** | `web/app/paciente/page.tsx:16` `CONFIDENCE_THRESHOLD = 70`; línea 99 filtra por confianza + descarta si domina "idle" |
| RF-06 | Permitir reportar traducción incorrecta/ambigua para mejorar el modelo | **NO IMPLEMENTADO** | Sin mecanismo de feedback/reporte en la UI de paciente/recepción (solo existe un `report` no relacionado en `web/app/parity/page.tsx`, herramienta interna de QA) |
| RNF-01 | Latencia <1s | **PARCIAL** | RNF-07 de `IDS.md`: p50/p95 documentados como "objetivos de diseño, no mediciones formales registradas" |
| RNF-02 | Accuracy ≥90% en entornos clínicos controlados | **PARCIAL / NO VERIFICADO** | Modelo entrenable (`train_lstm.py`) existe, pero no hay harness formal que valide el 90% como criterio de aceptación automatizado |
| RNF-03 | 100% sin almacenamiento persistente de video/imágenes | **IMPLEMENTADO** | Coincide con RNF-03 de `IDS.md` (estado en memoria + BroadcastChannel) |
| RNF-04 | Hardware estándar (cámaras, **pantallas de doble cara**) | **PARCIAL** | Cámara estándar sí (RNF-05 de `IDS.md`); no hay evidencia de "pantalla doble cara" ni estación física única — el sistema son dos páginas web independientes (`/paciente`, `/recepcion`), no un kiosco físico con doble visor |
| RNF-05 | Dataset ampliado al dominio clínico | **PARCIAL** | `dataset/custom_blendshapes/`, `dataset/custom_tasks/` existen (ver git status); cobertura/validación completa no verificable solo con código |
| RNF-06 | Dataset validado lingüísticamente por intérpretes oficiales | **NO VERIFICABLE EN CÓDIGO** | Es un proceso organizacional (paquete EDT 3.2.5), no una feature de software |
| RNF-07 | Estación fija con cámara, pantalla doble cara, micrófono, altavoces | **NO IMPLEMENTADO** | Mismo hallazgo que RNF-04: no hay concepto de estación física única con pantalla de doble cara en el código — actualmente son dos estaciones-navegador independientes |

### 8.2 Actores — oficial vs. `IDS.md`

| Actor oficial (Registro de Interesados) | ¿Existe en `IDS.md`? | Observación |
|---|---|---|
| Recepcionista | Sí (ACT-02) | Coherente — ya generaliza "recepción o enfermería" |
| Enfermero/a | Sí, fusionado en ACT-02 | El registro oficial los trata como interesados separados pero con igual rol/interés — fusión razonable, documentarla explícitamente |
| Personas que se comunican con LSA / Pacientes sordos | Sí (ACT-01) | Coherente |
| — (ningún interesado oficial equivalente) | ACT-03 "Administrador del Modelo" | **No existe como interesado/usuario en los documentos oficiales.** El trabajo de dataset/entrenamiento (EDT 3.2.2–3.2.5, 5.2.1–5.2.2) se describe como tarea del **equipo del proyecto**, no como un rol operativo del producto final. Es válido mantenerlo como actor de sistema si el software realmente expone un "Modo Captura" en producción, pero debe aclararse en el documento que es una decisión de diseño del equipo, no un requisito trazable a un interesado oficial. |
| Tutor, Cotutor, Estado (Ley 27.710), Comité de Ética, Natalia García Escudé, Competencia, creadores de datasets, librerías | No modelados (correcto) | Son interesados de gobernanza/proyecto, no actores del sistema — decisión correcta de excluirlos por Larman/UML 2.5 |

### 8.3 IDs y numeración — colisión crítica

- **Los RF-01..RF-06 y RNF-01..RNF-07 de la matriz oficial NO coinciden en contenido con los
  RF-01..RF-15 y RNF-01..RNF-07 de `docs/IDS.md`.** Por ejemplo, el RF-01 oficial ("traducir LSA a
  texto y voz") es una traducción libre de lo que en `IDS.md` está repartido en 6 requisitos
  (RF-01 a RF-06). Si se publican ambos documentos con la misma numeración pero contenido distinto,
  cualquier lector (incluido el tribunal) detectará una contradicción directa.
- Los criterios de aceptación CRIT-01..06 (y el CRIT-07 mencionado solo en la matriz, sección 3) no
  están referenciados en absoluto en `docs/IDS.md`.
- Los objetivos específicos OE01–OE10 (métricas cuantificadas) tampoco aparecen en `docs/IDS.md`,
  pese a que varios RNF nuestros (RNF-07 latencia, etc.) deberían citarlos como origen del objetivo
  medible.

### 8.4 Casos de uso — no hay contraparte oficial directa (esperado)

Los documentos de gobierno (TP0/TP1/TP2/EDT/riesgos) no definen casos de uso — es un artefacto que
corresponde a nuestra Fase 1. No hay gap de omisión aquí, pero **CU-06/CU-07/CU-08 (Modo Captura /
Gestión de Vocabulario / Entrenamiento)** no tienen respaldo directo en un requisito oficial de la
matriz (son found únicamente por inferencia desde el EDT, no desde RF/RNF oficiales) — deben
justificarse explícitamente como decisión de arquitectura del equipo, tal como se señala en 8.2.

---

## 9. Recomendaciones concretas por entregable (01–09)

1. **Actualizar `docs/IDS.md` (fuente única de IDs):**
   - Reservar los IDs `RF-01`..`RF-06` y `RNF-01`..`RNF-07` **exclusivamente** para el texto literal
     de la matriz oficial (sección 3 de este resumen), y renumerar los actuales requisitos técnicos
     derivados (captura de landmarks, WebSocket, umbral 70%, etc.) como sub-requisitos o
     requisitos técnicos con un prefijo distinto (p. ej. `RF-T-01`..`RF-T-15`) que se declaren
     trazables *hacia* el RF oficial correspondiente (muchos-a-uno). Esto elimina la colisión de
     IDs detectada en 8.3.
   - Agregar explícitamente **RF-03 (consentimiento), RF-04 (logs de auditoría) y RF-06 (reporte de
     error de traducción)** como requisitos pendientes de implementación (actualmente ausentes del
     código), y marcarlos como brecha conocida en el ERS.
   - Incorporar los **CRIT-01..07** y **OE01..OE10** como anexo de trazabilidad (Objetivo ↔ RF/RNF
     ↔ Criterio de aceptación), citando la matriz oficial como fuente.

2. **Modelo de Dominio / Casos de Uso (Entregables 01–02):** documentar explícitamente que
   ACT-03 "Administrador del Modelo" y CU-06/07/08 son una decisión de diseño del equipo sin
   respaldo directo en un interesado oficial (ver 8.2/8.4), para que quede trazado y no parezca un
   requisito inventado sin justificación ante el tribunal.

3. **ERS (IEEE 830):** incluir sección de trazabilidad Requisito↔Interesado usando exactamente los
   nombres/roles del Registro de Interesados oficial (p. ej. distinguir "Recepcionista" y
   "Enfermero/a" como interesados de origen aunque se modelen como un solo actor de sistema).

4. **RNF de hardware (RNF-04/RNF-07 oficiales):** decidir y documentar explícitamente el alcance
   real del "hardware de estación fija con pantalla de doble cara" — si el MVP entregado es
   software puro (dos páginas web en dispositivos separados) y no una estación física integrada,
   esto debe declararse como **desviación de alcance aprobada** (o como trabajo futuro fuera del
   MVP), no dejarse implícito.

5. **RNF de latencia y precisión (RNF-01/RNF-02 oficiales, CRIT-01/02/03):** agregar un
   entregable/sección de "Informe de Pruebas Controladas" (E05) con mediciones reales de latencia
   p50/p95 y accuracy, ya que hoy `IDS.md` documenta estos valores solo como "objetivos de diseño,
   no mediciones formales" — esto no cumple el criterio de aceptación oficial tal como está escrito.

6. **Riesgos (Entregable de gestión, no académico de software pero sí insumo de diseño):** priorizar
   en el diseño técnico mitigaciones para los riesgos "Inaceptables" ligados a paquetes de análisis
   y desarrollo (#1 validación lingüística, #5 latencia backend, #16 gestos no manuales/faciales,
   #4 iluminación) ya que impactan directamente RF-05, RNF-01, RNF-02 y RNF-05 oficiales.

7. **Nomenclatura de documento:** unificar el ID de proyecto a una sola grafía (`LSASALUD-G9`) en
   todos los entregables nuevos — actualmente varía entre `LSASALU D-G9`, `LSASALUD_G9` y
   `LSASALUD-G9` según el documento de origen.
