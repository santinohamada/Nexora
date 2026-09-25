"""gen_vista_fisica.py — genera 06_vista_fisica.drawio (Vista Física, Entregable 06).

PlantUML/smetana no logra un layout retrato legible para este diagrama (el
mismo motivo documentado en render.sh para el Modelo de Dominio y la Vista
de Desarrollo): al tener varios nodos hermanos muy conectados, smetana los
distribuye en fila en vez de columna. Por eso se genera a mano, en una sola
columna angosta, igual que gen_vista_desarrollo.py / gen_modelo_dominio.py.

Uso: C:\\Nexora\\venv\\Scripts\\python.exe gen_vista_fisica.py
Escribe docs/diagramas/arquitectura/06_vista_fisica.drawio.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).with_name("06_vista_fisica.drawio")

PKG = ("shape=folder;tabWidth=140;tabHeight=22;tabPosition=left;html=1;whiteSpace=wrap;"
       "verticalAlign=top;align=left;spacingLeft=8;spacingTop=2;fontStyle=1;fontSize=14;"
       "fillColor=#FFFFFF;strokeColor=#6B7280;fontColor=#1E448A;fontFamily=Helvetica;")
NODE = ("rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F7FA;strokeColor=#1E448A;"
        "fontStyle=1;fontSize=13;fontFamily=Helvetica;verticalAlign=top;align=left;spacingLeft=6;spacingTop=4;")
ARTIFACT = ("shape=note;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#6B7280;"
            "fontSize=12;fontFamily=Helvetica;size=10;")
FOLDER = ("shape=folder;tabWidth=36;tabHeight=12;html=1;whiteSpace=wrap;fillColor=#F5F7FA;"
          "strokeColor=#6B7280;fontSize=12;fontFamily=Helvetica;")
SUMMARY = ("rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor=#F5F7FA;strokeColor=#1E448A;"
           "fontSize=13;fontFamily=Helvetica;align=center;verticalAlign=middle;")
NOTE = ("shape=note;whiteSpace=wrap;html=1;fillColor=#FFF8DC;strokeColor=#B8860B;"
        "fontSize=12;fontFamily=Helvetica;align=left;spacingLeft=6;size=14;")
TITLE = "text;html=1;align=left;verticalAlign=middle;fontStyle=1;fontSize=15;fontFamily=Helvetica;"
DEP = ("endArrow=open;endSize=9;dashed=1;html=1;strokeColor=#333333;fontSize=12;"
       "fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;rounded=0;")
BIDIR = DEP + "startArrow=open;startSize=9;"


def vertex(cid, value, style, x, y, w, h):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def edge(cid, label, style, points, label_offset=None, label_pos=None):
    (sx, sy), (tx, ty) = points[0], points[-1]
    mids = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points[1:-1])
    arr = f'<Array as="points">{mids}</Array>' if mids else ""
    off = f'<mxPoint x="{label_offset[0]}" y="{label_offset[1]}" as="offset"/>' if label_offset else ""
    pos_attr = f' x="{label_pos}"' if label_pos is not None else ""
    return (f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" edge="1" parent="1">'
            f'<mxGeometry relative="1"{pos_attr} as="geometry"><mxPoint x="{sx}" y="{sy}" as="sourcePoint"/>'
            f'<mxPoint x="{tx}" y="{ty}" as="targetPoint"/>{arr}{off}</mxGeometry></mxCell>')


def build():
    c = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>',
         vertex("title", "Vista Física — LSA Salud (estaciones fijas de doble cara)", TITLE, 0, 0, 620, 28)]

    c.append(vertex("pkg", "Estación fija (ej.: Admisión)", PKG, 0, 40, 600, 620))
    c.append(vertex("pc", "PC de la estación", NODE, 15, 75, 570, 575))

    c.append(vertex("browser", "Navegador (Chrome)", NODE, 35, 105, 530, 115))
    c.append(vertex("tabP", "Cara del paciente<br>/paciente", NODE, 50, 138, 185, 60))
    c.append(vertex("tabR", "Cara del personal<br>/recepcion", NODE, 365, 138, 185, 60))

    c.append(vertex("next", "Next.js<br>:3000", NODE, 35, 290, 150, 50))
    c.append(vertex("backend", "FastAPI (Uvicorn)<br>:8000", NODE, 210, 290, 355, 130))
    c.append(vertex("appPy", "app.py", ARTIFACT, 230, 340, 90, 34))
    c.append(vertex("lstmPy", "lstm.py", ARTIFACT, 335, 340, 90, 34))
    c.append(vertex("piper", "Piper TTS", ARTIFACT, 440, 340, 100, 34))

    c.append(vertex("ollama", "Ollama<br>:11434", NODE, 35, 500, 150, 50))
    c.append(vertex("fs", "Archivos locales", NODE, 210, 480, 355, 150))
    c.append(vertex("fDataset", "dataset/", FOLDER, 225, 515, 75, 40))
    c.append(vertex("fModels", "models/", FOLDER, 310, 515, 75, 40))
    c.append(vertex("fVoices", "voices/", FOLDER, 395, 515, 75, 40))
    c.append(vertex("fLogs", "logs/", FOLDER, 480, 515, 70, 40))

    c.append(edge("e5", "BroadcastChannel", BIDIR, [(235, 168), (365, 168)], label_offset=(0, -14)))
    c.append(edge("e1", "HTTP (páginas)", DEP, [(110, 220), (110, 290)], label_offset=(-50, 0)))
    c.append(edge("e3", "WS + HTTP", DEP, [(225, 198), (225, 290)], label_offset=(36, 0)))
    c.append(edge("e4", "HTTP", DEP, [(445, 198), (445, 290)], label_offset=(22, 0)))
    c.append(edge("e6", "HTTP", DEP, [(250, 420), (250, 450), (110, 450), (110, 500)], label_offset=(0, -10)))
    c.append(edge("e7", "lee/escribe", DEP, [(420, 420), (420, 480)], label_offset=(40, 0)))

    c.append(vertex("otras", "<b>Estaciones de Recepción, Triaje y Guardia</b><br>"
                             "misma estructura interna, cada una como instancia independiente",
                     SUMMARY, 60, 680, 480, 60))

    c.append(vertex("note", "Cada estación es una instancia local independiente: navegador, Next.js, "
                             "FastAPI, Ollama y almacenamiento local propio. No hay servidor central ni "
                             "datos compartidos entre estaciones (RNF-T-02, RNF-03); cada una conserva su "
                             "propia conversación mientras dura la atención.",
                     NOTE, 30, 760, 540, 90))

    body = "".join(c)
    OUT.write_text(
        f'<mxfile><diagram name="Vista Física"><mxGraphModel><root>{body}</root></mxGraphModel></diagram></mxfile>',
        encoding="utf-8",
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
