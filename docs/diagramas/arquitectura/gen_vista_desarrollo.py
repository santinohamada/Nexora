from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).with_name("06_vista_desarrollo.drawio")

PKG = ("shape=folder;tabWidth=90;tabHeight=22;tabPosition=left;html=1;whiteSpace=wrap;"
       "verticalAlign=top;align=left;spacingLeft=8;spacingTop=2;fontStyle=1;fontSize=14;"
       "fillColor=#FFFFFF;strokeColor=#6B7280;fontColor=#1E448A;fontFamily=Helvetica;")
CLS = ("rounded=1;arcSize=12;html=1;whiteSpace=wrap;fillColor=#F5F7FA;strokeColor=#1E448A;"
       "fontStyle=1;fontSize=14;fontFamily=Helvetica;")
FOLDER = ("shape=folder;tabWidth=36;tabHeight=12;html=1;whiteSpace=wrap;fillColor=#F5F7FA;"
          "strokeColor=#6B7280;fontSize=14;fontFamily=Helvetica;")
NOTE = ("shape=note;whiteSpace=wrap;html=1;fillColor=#FFF8DC;strokeColor=#B8860B;"
        "fontSize=13;fontFamily=Helvetica;align=left;spacingLeft=6;size=12;")
DEP = ("endArrow=open;endSize=10;dashed=1;html=1;strokeColor=#333333;fontSize=13;"
       "fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;rounded=0;")
TITLE = "text;html=1;align=left;verticalAlign=middle;fontStyle=1;fontSize=15;fontFamily=Helvetica;"

BOXES = {}


def vertex(cid, value, style, x, y, w, h):
    BOXES[cid] = (x, y, w, h)
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def at(cid, fx, fy):
    x, y, w, h = BOXES[cid]
    return (x + w * fx, y + h * fy)


def edge(cid, label, points, offset=(0, 0)):
    (sx, sy), (tx, ty) = points[0], points[-1]
    mids = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points[1:-1])
    arr = f'<Array as="points">{mids}</Array>' if mids else ""
    return (f'<mxCell id="{cid}" value="{escape(label)}" style="{DEP}" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry"><mxPoint x="{sx}" y="{sy}" as="sourcePoint"/>'
            f'<mxPoint x="{tx}" y="{ty}" as="targetPoint"/>{arr}'
            f'<mxPoint x="{offset[0]}" y="{offset[1]}" as="offset"/></mxGeometry></mxCell>')


def build():
    c = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>',
         vertex("title", "Vista de Desarrollo — LSA Salud (paquetes y dependencias)", TITLE, 0, 0, 760, 28)]

    c.append(vertex("web", "web/", PKG, 0, 40, 760, 250))
    c.append(vertex("webApp", "app/", CLS, 305, 74, 150, 42))
    c.append(vertex("webHooks", "hooks/", CLS, 60, 150, 150, 42))
    c.append(vertex("webComp", "components/", CLS, 550, 150, 150, 42))
    c.append(vertex("webLib", "lib/", CLS, 305, 226, 150, 42))

    c.append(vertex("src", "src/", PKG, 0, 340, 200, 100))
    c.append(vertex("model", "model/", CLS, 15, 378, 170, 42))
    c.append(vertex("appPy", "app.py", CLS, 300, 372, 170, 44))
    c.append(vertex("capVal", "capture_validation.py", CLS, 560, 372, 200, 44))

    c.append(vertex("train", "train_lstm.py", CLS, 15, 500, 170, 44))
    c.append(vertex("evalModel", "eval_model.py", CLS, 300, 500, 170, 44))
    c.append(vertex("docs", "docs/", FOLDER, 0, 790, 150, 44))
    c.append(vertex("noteDocs", "Documentación del proyecto;<br>sin dependencias de código.", NOTE, 170, 789, 220, 46))

    c.append(vertex("datos", "datos (sistema de archivos)", PKG, 260, 650, 500, 110))
    c.append(vertex("fDataset", "dataset/", FOLDER, 275, 694, 110, 44))
    c.append(vertex("fModels", "models/", FOLDER, 395, 694, 110, 44))
    c.append(vertex("fVoices", "voices/", FOLDER, 515, 694, 110, 44))
    c.append(vertex("fLogs", "logs/", FOLDER, 635, 694, 115, 50))

    hx, hy = at("webHooks", 0.5, 1)
    kx, ky = at("webComp", 0.5, 1)
    ax, ay, aw, ah = BOXES["appPy"]
    web_bottom = 290

    c.append(edge("e1", "usa", [at("webApp", 0.25, 1), (ax + 20, 133), at("webHooks", 0.8, 0)]))
    c.append(edge("e2", "usa", [at("webApp", 0.75, 1), (ax + 150, 133), at("webComp", 0.2, 0)]))
    c.append(edge("e3", "usa", [at("webHooks", 0.8, 1), (175, 247), at("webLib", 0, 0.5)]))
    c.append(edge("e4", "usa", [at("webComp", 0.2, 1), (580, 247), at("webLib", 1, 0.5)]))
    c.append(edge("e5", "HTTP / WS", [(hx, hy), (hx, web_bottom + 18), (ax + aw * 0.3, web_bottom + 18), (ax + aw * 0.3, ay)]))
    c.append(edge("e6", "HTTP", [(kx, ky), (kx, web_bottom + 34), (ax + aw * 0.7, web_bottom + 34), (ax + aw * 0.7, ay)]))
    c.append(edge("e7", "usa", [at("appPy", 0, 0.5), at("model", 1, 0.4)]))
    c.append(edge("e8", "usa", [at("appPy", 1, 0.5), at("capVal", 0, 0.5)]))
    c.append(edge("e9", "usa", [at("train", 0.5, 0), at("model", 0.5, 1)]))
    c.append(edge("e10", "usa (E05)", [at("evalModel", 0.5, 0), at("appPy", 0.5, 1)]))
    c.append(edge("e11", "lee/escribe dataset/<br>lee models/ y voices/", [at("appPy", 0.9, 1), (ax + aw * 0.9, 650)], offset=(80, 0)))
    c.append(edge("e12", "escribe logs/<br>(auditoría, reportes)", [at("appPy", 0.3, 1), (250, 416), (250, 655), (270, 655)]))
    tx, ty = at("train", 0.5, 1)
    c.append(edge("e13", "lee dataset/<br>escribe models/", [(tx, ty), (tx, 705), (260, 705)]))

    body = "".join(c)
    OUT.write_text(f'<mxfile><diagram name="Vista de Desarrollo"><mxGraphModel><root>{body}</root>'
                   f'</mxGraphModel></diagram></mxfile>', encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
