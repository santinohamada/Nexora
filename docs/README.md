# Documentación académica de LSA Salud

Este directorio contiene los entregables académicos de Ingeniería de
Software del proyecto **LSA Salud** (UTN-FRT, Proyecto Final), escritos en
LaTeX siguiendo la metodología de Larman (UML y Patrones, Proceso
Unificado), vistas arquitectónicas lógica y física, y UML 2.5. El nombre del repositorio de
código, "Nexora", es un alias técnico interno y no el nombre del proyecto
académico.

## Estructura

```
docs/
├── IDS.md                      # Registro canónico de IDs (actores, CU, RF, RNF, pantallas...), compartido por todos los TP
├── tools/
│   └── plantuml-1.2026.8.jar    # Jar de PlantUML embebido (no requiere instalación aparte)
├── referencias/                 # Material de contexto (no versionado, salvo RESUMEN_REFERENCIAS.md)
├── TP7/                         # TP7 — Análisis y Diseño (autocontenido)
│   ├── lsasalud.sty             # Estilo (portada, tablas, \diagrama, etc.)
│   ├── TP7_Análisis y Diseño.tex/.pdf   # Documento maestro con los 9 entregables (\part por entregable)
│   ├── 0N_Nombre_Entregable.tex # Wrapper standalone de cada entregable (portada + \input propio)
│   ├── contenido/
│   │   └── 0N_nombre_entregable.tex   # Cuerpo de cada entregable (sin preámbulo, se reutiliza
│   │                                   # tanto en el wrapper standalone como en el maestro)
│   ├── diagramas/
│   │   ├── _estilo.iuml         # skinparams compartidos (incluir con !include _estilo.iuml)
│   │   ├── 0N_*.puml            # Fuente de cada diagrama PlantUML
│   │   ├── casos_uso/           # gen_casos_uso.py → 02_casos_uso.drawio
│   │   ├── colaboracion/        # gen_drawio.py → 08_colaboracion_dc0N.drawio (DC-01..DC-09)
│   │   ├── dominio/             # gen_modelo_dominio.py → 01_modelo_dominio.drawio
│   │   └── arquitectura/        # gen_vista_logica.py / gen_vista_fisica.py
│   ├── img/
│   │   └── 0N_*.pdf             # Diagramas renderizados (generados por render.sh, no editar a mano)
│   ├── build/                   # PDF compilados (no versionado)
│   └── render.sh                # Script de renderizado de diagramas
└── TP8/                         # TP8 — Testing
    └── Enunciado/               # Enunciado y plantillas de la cátedra (no versionado)
```

Entregables (numeración según el orden del Documento Maestro):

| # | Entregable | Código | Wrapper | Cuerpo |
|---|------------|--------|---------|--------|
| 01 | Modelo de Dominio | `LSASALUD-G9-MD` | `01_Modelo_Dominio.tex` | `contenido/01_modelo_dominio.tex` |
| 02 | Diagrama de Casos de Uso | `LSASALUD-G9-DCU` | `02_Diagrama_Casos_Uso.tex` | `contenido/02_diagrama_casos_uso.tex` |
| 03 | Modelos de Casos de Uso | `LSASALUD-G9-MCU` | `03_Modelos_Casos_Uso.tex` | `contenido/03_modelos_casos_uso.tex` |
| 04 | Mockups | `LSASALUD-G9-MCK` | `04_Mockups.tex` | `contenido/04_mockups.tex` |
| 05 | ERS (IEEE Std 830-1998) | `LSASALUD-G9-ERS` | `05_ERS_IEEE830.tex` | `contenido/05_ers_ieee830.tex` |
| 06 | Arquitectura: Vistas (Lógica y Física) | `LSASALUD-G9-ARQ` | `06_Arquitectura_Vistas.tex` | `contenido/06_arquitectura_vistas.tex` |
| 07 | Casos de Uso Reales | `LSASALUD-G9-CUR` | `07_Casos_Uso_Reales.tex` | `contenido/07_casos_uso_reales.tex` |
| 08 | Diagramas de Colaboración | `LSASALUD-G9-DCO` | `08_Diagramas_Colaboracion.tex` | `contenido/08_diagramas_colaboracion.tex` |
| 09 | Modelo de Base de Datos | `LSASALUD-G9-MBD` | `09_Modelo_Datos.tex` | `contenido/09_modelo_datos.tex` |
| — | TP7 Análisis y Diseño (documento maestro) | `LSASALUD-G9-DM` | `TP7_Análisis y Diseño.tex` | (agrupa los 9 anteriores) |

`IDS.md` es la fuente única de verdad para todo identificador (actor, caso
de uso, requisito, concepto de dominio, pantalla, operación de sistema,
diagrama de colaboración) reutilizado entre entregables: cualquier cambio de
nombre o numeración se hace primero ahí. También documenta la trazabilidad
completa hacia la matriz de requisitos (`RF-01..06`,
`RNF-01..07`, reservados para su texto literal) y la realización de los
requisitos **RF-03 (consentimiento), RF-04 (auditoría) y RF-06
(reporte de traducción)** (CU-09, CU-10, CU-11; Diálogo de Consentimiento
P-05 dentro de `PacientePage`; DC-06, DC-07, DC-08; módulo
`storage.py` dentro de `app.py` en Arquitectura; eventos de
auditoría y reportes persistidos en la base de datos SQLite `data/lsa_salud.db`
en el Modelo de Datos).

## Regenerar los diagramas

Los diagramas se escriben en PlantUML (`diagramas/*.puml`) y se renderizan a
PDF vectorial en `img/`. El `.jar` de PlantUML (versión `1.2026.8`) no se
versiona: se descarga una vez en `tools/` con

```bash
gh release download v1.2026.8 -R plantuml/plantuml -p plantuml-1.2026.8.jar -D docs/tools
```

o manualmente desde https://github.com/plantuml/plantuml/releases/tag/v1.2026.8.

Las rutas de las herramientas se configuran con variables de entorno (por
defecto se buscan en el `PATH`): `JAVA`, `PLANTUML_JAR`, `PYTHON` (con el
venv del proyecto) y `DRAWIO` (ejecutable de draw.io desktop). Ejemplo en
Windows (Git Bash):

```bash
cd docs/TP7/
JAVA="/c/Program Files/Microsoft/jdk-21.0.12.101-hotspot/bin/java.exe" \
PYTHON="$(cd .. && pwd)/venv/Scripts/python.exe" \
DRAWIO="$LOCALAPPDATA/Programs/draw.io/draw.io.exe" \
./render.sh
```

`PYTHON` y `DRAWIO` deben ser rutas absolutas (o comandos del `PATH`),
porque `render.sh` cambia de carpeta para correr cada generador.

Requisitos:

- **Java 21** (o superior), en el `PATH` o indicado con `JAVA`.
- No hace falta Graphviz: los `.puml` usan `!pragma layout smetana`
  (motor de layout interno de PlantUML), declarado en `diagramas/_estilo.iuml`
  e incluido al inicio de cada diagrama con `!include _estilo.iuml`.

Para renderizar todo:

```bash
cd docs/TP7/
./render.sh
```

Esto ejecuta PlantUML sobre todos los `diagramas/*.puml` y escribe el PDF
correspondiente en `img/`. Cualquier error de sintaxis PlantUML se imprime
en la consola; el objetivo es siempre correr con cero errores antes de
compilar el LaTeX.

Para agregar un diagrama nuevo: crear `diagramas/NN_nombre.puml` empezando
con `@startuml NN_nombre` seguido de `!include _estilo.iuml`, correr
`./render.sh`, y referenciarlo desde el `.tex` correspondiente con
`\diagrama{NN_nombre}{ancho}{caption}{label}` (macro definida en
`lsasalud.sty`, ya apunta a `img/NN_nombre.pdf`).

### Diagramas de casos de uso: formato de referencia

El diagrama de casos de uso usa el siguiente formato: un único rectángulo de
límite del sistema titulado "LSA Salud", sin paquetes, casos de uso como
elipses de fondo amarillo pálido (`#FFF2CC`) organizadas en columnas, y
actores como figuras de palito fuera del límite (paciente a la izquierda,
personal y equipo a la derecha), unidos por líneas rectas.

Como PlantUML no permite fijar posiciones, este diagrama se genera con
draw.io: `diagramas/casos_uso/gen_casos_uso.py` define las posiciones y
relaciones y escribe `02_casos_uso.drawio` (editable en draw.io), que
`render.sh` exporta a `img/02_casos_uso.pdf`.

### Diagramas de colaboración (DC-01..DC-09): draw.io, no PlantUML

Los 9 diagramas de colaboración de `contenido/08_diagramas_colaboracion.tex`
(DC-06 a DC-08 cubren RF-03/04/06; DC-09 cubre RNF-03) son un caso aparte: PlantUML
no permite expresar la notación exacta de Larman/UML 2.5 (enlace sin punta
de flecha + una flechita propia y paralela por cada mensaje). Por eso se
generan como archivos **draw.io** (`.drawio`, XML editable) en
`diagramas/colaboracion/`:

- `gen_drawio.py` (correr con el Python del venv del proyecto) define
  declarativamente los objetos, enlaces y mensajes de cada diagrama y
  calcula la geometría (enlace recto sin flecha, mensajes como flechitas
  cortas paralelas al enlace, apiladas cuando comparten enlace, automensajes
  como bucle sobre el objeto). Escribe los 9 `08_colaboracion_dc0N.drawio`.
  Para agregar un diagrama nuevo, sumar una función `dcNN()` que devuelva un
  `Diagram` (ver `dc06`/`dc07`/`dc08`/`dc09` como ejemplo de cadena
  horizontal simple) y registrarla en la tupla de `main()`.
- Esos `.drawio` se pueden abrir y editar a mano en la aplicación de
  escritorio de draw.io (`https://github.com/jgraph/drawio-desktop`,
  en Windows se instala con `winget install JGraph.Draw`) si hace falta un
  ajuste puntual de layout.
- Para exportar a PDF vectorial recortado (lo que consume el `.tex`):

  ```bash
  "$DRAWIO" \
    --export --format pdf --crop \
    --output docs/TP7/img/08_colaboracion_dc01.pdf \
    docs/TP7/diagramas/colaboracion/08_colaboracion_dc01.drawio
  ```

  `render.sh` ya hace esto automáticamente para los 9 diagramas después de
  correr `gen_drawio.py`.
- Si se edita un `.drawio` a mano, no volver a correr `gen_drawio.py`
  encima (lo sobrescribe); si se necesita regenerar desde cero, ajustar la
  especificación en `gen_drawio.py` en su lugar.

## Compilar en Overleaf

1. Subí la carpeta `docs/TP7/` completa a un proyecto de Overleaf (o subí un
   `.zip` de la carpeta), preservando la estructura de subcarpetas
   (`lsasalud.sty`, `contenido/`, `img/`, `IDS.md` es solo referencia y no
   hace falta subirlo si el proyecto ya está completo).
2. Compilador: **pdfLaTeX** (el paquete usa `babel[spanish]`, `hyperref`,
   `booktabs`, `longtable`, `tabularx`, `titlesec`, `tocloft`, `listings`,
   todos estándar en TeX Live/Overleaf; no se requiere XeLaTeX ni LuaLaTeX).
3. Documento principal: `TP7_Análisis y Diseño.tex` (los nueve
   entregables juntos, con tabla de contenidos, lista de figuras y lista de
   tablas), o cualquier `0N_Nombre_Entregable.tex` individual si solo se
   necesita compilar un entregable suelto.
4. Los diagramas ya están renderizados como PDF en `img/`; no hace falta
   Java ni PlantUML dentro de Overleaf, solo los `.pdf` versionados en esa
   carpeta.

## Convenciones

- Los cuerpos de `contenido/` no tienen `\documentclass` ni
  `\begin{document}`: se incluyen tanto desde su wrapper standalone como
  desde el Documento Maestro, donde quedan dentro de un `\part`.
- La numeración de `\section` se reinicia en cada `\part`
  (`\counterwithin*{section}{part}` en `lsasalud.sty`), así que cada cuerpo
  puede empezar siempre en `\section{...}` sin coordinarse con los demás.
- Las figuras y tablas usan etiquetas prefijadas por entregable
  (`fig:dom-...`, `tab:ers-...`, `fig:mock-...`, `fig:arq-...`,
  `fig:cur-...`, `fig:col-...`, `fig:dat-...`) para evitar colisiones al
  unir todo en el Documento Maestro.
- No se editan a mano los PDF de `img/`: siempre se regeneran con
  `render.sh` a partir del `.puml` correspondiente.
- `\portada{título}{código}` (definida en `lsasalud.sty`) recibe el título
  del entregable y su código de documento (`LSASALUD-G9-<sigla>`, esquema
  propio del equipo); imprime el bloque de encabezado (ID de
  proyecto, cliente, preparado por, director, tutor, cotutor, fecha,
  versión) sin logo, según decisión del equipo de retirar el logo de
  "Nexora" de las portadas.
- Los entregables describen el sistema LSA Salud completo, tal como se
  construirá: RF-03, RF-04 y RF-06 (consentimiento, auditoría,
  reporte de traducción) se describen igual que el resto de los requisitos,
  en presente/futuro declarativo. Ningún entregable usa lenguaje de avance de
  código.
- `docs/referencias/` contiene material de contexto académico que este
  documento no referencia.
