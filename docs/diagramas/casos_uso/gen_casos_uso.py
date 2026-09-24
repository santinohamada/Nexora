from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).with_name("02_casos_uso.drawio")

EW, EH = 180, 62
COL = {"L": 190, "C": 385, "R": 580}

USE_CASES = {
    "CU09": ("CU-09<br>Otorgar Consentimiento<br>Explícito de Cámara", "L", 70),
    "CU02": ("CU-02<br>Traducir Secuencia de Señas<br>a Oración Natural", "L", 185),
    "CU01": ("CU-01<br>Comunicarse mediante<br>Lengua de Señas Argentina", "L", 300),
    "CU03": ("CU-03<br>Sintetizar Oración<br>en Voz", "L", 415),
    "CU10": ("CU-10<br>Reportar Traducción<br>Incorrecta o Ambigua", "C", 185),
    "CU11": ("CU-11<br>Registrar Evento<br>de Auditoría", "C", 415),
    "CU05": ("CU-05<br>Dictar Respuesta<br>por Voz", "R", 185),
    "CU04": ("CU-04<br>Responder al Paciente", "R", 300),
    "CU06": ("CU-06<br>Capturar Muestra de Seña<br>para Entrenamiento", "R", 500),
    "CU07": ("CU-07<br>Gestionar Vocabulario<br>de Señas", "R", 600),
    "CU08": ("CU-08<br>Entrenar el Modelo<br>de Reconocimiento", "R", 700),
}

ACTORS = {
    "Paciente": ("Paciente", 70, 250),
    "Personal": ("Personal de Recepción<br>o Enfermería", 870, 270),
    "Dev": ("Desarrollador de IA /<br>Equipo de Proyecto", 870, 570),
}

ASSOCIATIONS = [
    ("Paciente", "CU09"),
    ("Paciente", "CU01"),
    ("Personal", "CU04"),
    ("Dev", "CU06"),
    ("Dev", "CU08"),
]

DEPENDENCIES = [
    ("CU01", "CU02", "«include»"),
    ("CU01", "CU03", "«include»"),
    ("CU01", "CU11", "«include»"),
    ("CU04", "CU11", "«include»"),
    ("CU06", "CU07", "«include»"),
    ("CU05", "CU04", "«extend»"),
    ("CU10", "CU01", "«extend»"),
    ("CU10", "CU04", "«extend»"),
]

BOUNDARY = (160, 20, 640, 780)

ELLIPSE = "ellipse;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#7F6000;fontFamily=Helvetica;fontSize=12;"
ACTOR = "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor=#FFFFFF;strokeColor=#1A1A1A;fontFamily=Helvetica;fontSize=12;"
BOX = "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#333333;verticalAlign=top;fontStyle=1;fontFamily=Helvetica;fontSize=13;spacingTop=6;"
ASSOC = "endArrow=none;html=1;strokeColor=#333333;"
DEP = "endArrow=open;endSize=10;dashed=1;html=1;strokeColor=#555555;fontFamily=Helvetica;fontSize=12;labelBackgroundColor=#FFFFFF;"


def cell(cid, value, style, x, y, w, h):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def edge(cid, src, dst, style, value=""):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')


def build():
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    bx, by, bw, bh = BOUNDARY
    cells.append(cell("boundary", "LSA Salud", BOX, bx, by, bw, bh))
    for cid, (label, col, y) in USE_CASES.items():
        cells.append(cell(cid, label, ELLIPSE, COL[col], y, EW, EH))
    for cid, (label, x, y) in ACTORS.items():
        cells.append(cell(cid, label, ACTOR, x, y, 30, 60))
    for i, (a, b) in enumerate(ASSOCIATIONS):
        cells.append(edge(f"as{i}", a, b, ASSOC))
    for i, (a, b, kind) in enumerate(DEPENDENCIES):
        cells.append(edge(f"dp{i}", a, b, DEP, kind))
    body = "".join(cells)
    OUT.write_text(
        f'<mxfile><diagram name="Casos de Uso"><mxGraphModel><root>{body}</root></mxGraphModel></diagram></mxfile>',
        encoding="utf-8",
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
