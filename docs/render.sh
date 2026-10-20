#!/usr/bin/env bash
# render.sh — Renderiza todos los diagramas de docs/ a PDF vectorial en img/.
#
# 1. Diagramas PlantUML (diagramas/*.puml, salvo casos de uso y colaboración):
#    requiere Java 21 y el jar embebido en tools/. No requiere Graphviz
#    (los .puml usan !pragma layout smetana).
# 2. Diagramas de colaboración (diagramas/colaboracion/08_colaboracion_dc0N):
#    se generan como .drawio editables con gen_drawio.py y se exportan a PDF
#    con draw.io desktop. Requiere el venv de Python y draw.io instalado.
# 3. Diagrama de casos de uso (diagramas/casos_uso/gen_casos_uso.py): mismo
#    flujo draw.io (límite único del sistema, actores a ambos lados).
# 4. Modelo de Dominio (diagramas/dominio/gen_modelo_dominio.py) y Vistas
#    Lógica y Física (diagramas/arquitectura/gen_vista_*.py): mismo flujo
#    draw.io; se generaron a mano (en vez de PlantUML/smetana) porque esos
#    grafos muy interconectados no entran en formato retrato legible con el
#    layout automático de smetana (ver guía de figuras del entregable).
#
# Uso: ejecutar desde docs/  ->  ./render.sh
set -euo pipefail
cd "$(dirname "$0")"

JAVA="${JAVA:-java}"
JAR="${PLANTUML_JAR:-tools/plantuml-1.2026.8.jar}"
PYTHON="${PYTHON:-python}"
DRAWIO="${DRAWIO:-draw.io}"

if [ ! -f "$JAR" ]; then
  echo "Falta $JAR. Descargalo con:" >&2
  echo "  gh release download v1.2026.8 -R plantuml/plantuml -p plantuml-1.2026.8.jar -D docs/tools" >&2
  exit 1
fi

"$JAVA" -jar "$JAR" -tpdf -o ../img diagramas/*.puml

(
  cd diagramas/colaboracion
  "$PYTHON" gen_drawio.py
  for n in 01 02 03 04 05 06 07 08 09; do
    "$DRAWIO" --export --format pdf --crop \
      --output "../../img/08_colaboracion_dc$n.pdf" \
      "08_colaboracion_dc$n.drawio"
  done
)

(
  cd diagramas/casos_uso
  "$PYTHON" gen_casos_uso.py
  "$DRAWIO" --export --format pdf --crop \
    --output "../../img/02_casos_uso.pdf" "02_casos_uso.drawio"
)

(
  cd diagramas/arquitectura
  "$PYTHON" gen_vista_logica.py
  "$DRAWIO" --export --format pdf --crop \
    --output "../../img/06_vista_logica.pdf" "06_vista_logica.drawio"
  "$PYTHON" gen_vista_fisica.py
  "$DRAWIO" --export --format pdf --crop \
    --output "../../img/06_vista_fisica.pdf" "06_vista_fisica.drawio"
)

(
  cd diagramas/dominio
  "$PYTHON" gen_modelo_dominio.py
  "$DRAWIO" --export --format pdf --crop \
    --output "../../img/01_modelo_dominio.pdf" "01_modelo_dominio.drawio"
)
