import re
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).with_name("06_vista_logica.drawio")

PKG = ("shape=folder;tabWidth=150;tabHeight=24;tabPosition=left;html=1;whiteSpace=wrap;"
       "verticalAlign=top;align=left;spacingLeft=8;spacingTop=2;fontStyle=1;fontSize=14;"
       "fillColor=#FFFFFF;strokeColor=#6B7280;fontColor=#1E448A;fontFamily=Helvetica;")
CLS = ("rounded=1;arcSize=12;html=1;whiteSpace=wrap;fillColor=#F5F7FA;strokeColor=#1E448A;"
       "fontStyle=1;fontSize=14;fontFamily=Helvetica;")
DEP = ("endArrow=open;endSize=10;dashed=1;html=1;strokeColor=#333333;fontSize=13;"
       "fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;")
USE = "endArrow=open;endSize=10;html=1;strokeColor=#333333;"
TITLE = "text;html=1;align=left;verticalAlign=middle;fontStyle=1;fontSize=15;fontFamily=Helvetica;"

W, H = 170, 34

PACKAGES = [
    ("front", "Frontend (Next.js / React)", 0, 40, 800, 500),
    ("app", "app (páginas)", 20, 80, 760, 110),
    ("hooks", "hooks", 20, 230, 380, 170),
    ("comp", "components", 420, 230, 360, 130),
    ("lib", "lib", 20, 430, 210, 90),
    ("back", "Backend (FastAPI)", 0, 580, 800, 160),
]

CLASSES = [
    ("pLanding", "page (P-01)", 35, 130, 120),
    ("pRecepcion", "recepcion/page (P-03)", 170, 130, 175),
    ("pPaciente", "paciente/page (P-02, incluye diálogo\nde consentimiento P-05)", 420, 124, 250, 44),
    ("uMP", "useMediaPipe", 35, 270),
    ("uWS", "useSignWebSocket", 215, 270),
    ("uSB", "useSentenceBuilder", 35, 315),
    ("uChat", "useChatChannel", 215, 315),
    ("uSTT", "useSpeechToText", 35, 360),
    ("cTop", "TopPredictions", 435, 270, 165),
    ("cCapture", "CaptureMode", 605, 270, 165),
    ("cBubble", "ChatBubble", 435, 315, 165),
    ("cRec", "ReceptionControls", 605, 315, 165),
    ("mpLib", "mediapipe.ts", 40, 470),
    ("appPy", "app.py", 315, 620),
    ("lstm", "SignLanguageLSTM", 60, 685),
    ("capVal", "capture_validation", 315, 685),
]

EDGES = [
    ("app", "hooks", DEP, "usa"),
    ("app", "comp", DEP, "usa"),
    ("hooks", "lib", DEP, ""),
    ("hooks", "appPy", DEP, "WS / HTTP"),
    ("comp", "appPy", DEP, "HTTP"),
    ("appPy", "lstm", USE, ""),
    ("appPy", "capVal", USE, ""),
]



def fit_tab(value, style):
    if not style.startswith("shape=folder") or "tabPosition=left" not in style:
        return style
    size = int(re.search(r"fontSize=(\d+)", style).group(1))
    text = re.sub(r"<[^>]+>", "", value)
    width = round(len(text) * size * 0.62 + 24)
    return re.sub(r"tabWidth=\d+", f"tabWidth={width}", style)

def vertex(cid, value, style, x, y, w, h, parent="1"):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{fit_tab(value, style)}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def edge(cid, s, t, style, value):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" edge="1" parent="1" source="{s}" target="{t}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')


def build():
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(vertex("title", "Vista Lógica — LSA Salud (módulos de diseño)", TITLE, 0, 0, 800, 30))
    for cid, label, x, y, w, h in PACKAGES:
        cells.append(vertex(cid, label, PKG, x, y, w, h))
    for spec in CLASSES:
        cid, label, x, y = spec[:4]
        w = spec[4] if len(spec) > 4 else W
        h = spec[5] if len(spec) > 5 else H
        cells.append(vertex(cid, label, CLS, x, y, w, h))
    for i, (s, t, style, value) in enumerate(EDGES):
        cells.append(edge(f"e{i}", s, t, style, value))
    OUT.write_text(f'<mxfile><diagram name="Vista Lógica"><mxGraphModel><root>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>', encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
