"""Genera 06_vista_desarrollo.drawio: Vista de Desarrollo de LSA Salud
(paquetes del repositorio y sus dependencias), en una cuadrícula angosta de
tres columnas para que el PDF exportado quede en formato retrato (en vez del
layout ancho que producía PlantUML/smetana para este grafo con varios nodos
"hub"; ver docs/render.sh y la guía de figuras). Mismo estilo que
gen_vista_logica.py. Mismos elementos y dependencias que el .puml original
que reemplaza.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).with_name("06_vista_desarrollo.drawio")

PKG = ("shape=folder;tabWidth=90;tabHeight=22;tabPosition=left;html=1;whiteSpace=wrap;"
       "verticalAlign=top;align=left;spacingLeft=8;spacingTop=2;fontStyle=1;fontSize=14;"
       "fillColor=#FFFFFF;strokeColor=#6B7280;fontColor=#1E448A;fontFamily=Helvetica;")
CLS = ("rounded=1;arcSize=12;html=1;whiteSpace=wrap;fillColor=#F5F7FA;strokeColor=#1E448A;"
       "fontStyle=1;fontSize=13;fontFamily=Helvetica;")
FOLDER = ("shape=folder;tabWidth=40;tabHeight=14;html=1;whiteSpace=wrap;fillColor=#F5F7FA;"
          "strokeColor=#1E448A;fontStyle=0;fontSize=13;fontFamily=Helvetica;verticalAlign=bottom;")
DEP = ("endArrow=open;endSize=10;dashed=1;html=1;strokeColor=#333333;fontSize=11;"
       "fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;edgeStyle=orthogonalEdgeStyle;rounded=0;")
NOTE = ("shape=note;whiteSpace=wrap;html=1;fillColor=#FFF8DC;strokeColor=#B8860B;"
        "fontSize=11;fontFamily=Helvetica;align=left;size=12;")
TITLE = "text;html=1;align=left;verticalAlign=middle;fontStyle=1;fontSize=15;fontFamily=Helvetica;"


def vertex(cid, value, style, x, y, w, h, parent="1"):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def edge(cid, s, t, style, value, exit_side=None, entry_side=None, points=None, label_x=None, parent="1"):
    st = style
    if exit_side:
        st += exit_side
    if entry_side:
        st += entry_side
    pts = ""
    if points:
        pts = "<Array as=\"points\">" + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
    lx = f' x="{label_x}"' if label_x is not None else ""
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{st}" edge="1" parent="{parent}" source="{s}" target="{t}">'
            f'<mxGeometry relative="1" as="geometry"{lx}>{pts}</mxGeometry></mxCell>')


def build():
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(vertex("title", "Vista de Desarrollo — LSA Salud (paquetes y dependencias)", TITLE, 0, 0, 560, 28))

    # --- Paquete web/: WebApp arriba, WebHooks/WebComponents en la fila
    # intermedia (uno al lado del otro), WebLib abajo. Así ningún par
    # depende-de salta sobre otra caja (evita las líneas que atravesaban
    # texto en el primer intento).
    WEB_X, WEB_Y, WEB_W = 0, 40, 300
    CW, CH = 130, 42
    cells.append(vertex("Web", "web/", PKG, WEB_X, WEB_Y, WEB_W, 3 * CH + 3 * 22 + 30))
    top_y = WEB_Y + 34
    mid_y = top_y + CH + 22
    bot_y = mid_y + CH + 22
    cells.append(vertex("WebApp", "app/", CLS, WEB_X + (WEB_W - CW) / 2, top_y, CW, CH))
    cells.append(vertex("WebHooks", "hooks/", CLS, WEB_X + 15, mid_y, CW, CH))
    cells.append(vertex("WebComponents", "components/", CLS, WEB_X + WEB_W - 15 - CW, mid_y, CW, CH))
    cells.append(vertex("WebLib", "lib/", CLS, WEB_X + (WEB_W - CW) / 2, bot_y, CW, CH))
    web_bottom = bot_y + CH

    # --- Paquete src/, debajo de web/. ---
    src_y = web_bottom + 34
    cells.append(vertex("Src", "src/", PKG, WEB_X, src_y, 180, 30 + CH + 20))
    cells.append(vertex("SrcModel", "model/", CLS, WEB_X + 15, src_y + 34, CW, CH))

    # --- Columna 2: componentes Python. ---
    COL2_X, COL2_W = WEB_W + 110, 190
    COMP_H = 42
    comp_y = {}
    y = WEB_Y + 10
    for cid, label in [("AppPy", "app.py"), ("CaptureVal", "capture_validation.py"),
                        ("TrainLstm", "train_lstm.py"), ("AuditLog", "«diseñado»<br>audit_log.py")]:
        cells.append(vertex(cid, label, CLS, COL2_X, y, COL2_W, COMP_H))
        comp_y[cid] = y
        y += COMP_H + 90

    # --- Columna 3: carpetas de datos. ---
    COL3_X, COL3_W = COL2_X + COL2_W + 110, 150
    FOLDER_H = 44
    folder_y = {}
    y = WEB_Y + 10
    for cid, label in [("Dataset", "dataset/"), ("Models", "models/"), ("Voices", "voices/"),
                        ("Docs", "docs/"), ("Logs", "«diseñado»<br>logs/")]:
        cells.append(vertex(cid, label, FOLDER, COL3_X, y, COL3_W, FOLDER_H))
        folder_y[cid] = y
        # Docs lleva una nota debajo: reservar espacio extra antes de la
        # siguiente caja (Logs) para que la nota no la solape.
        y += FOLDER_H + (95 if cid == "Docs" else 85)

    # Notas (debajo de sus cajas, con espacio propio reservado en el layout).
    cells.append(vertex("noteDocs", "Documentación del proyecto (este<br>entregable y los demás). Sin<br>dependencias de código.",
                         NOTE, COL3_X, folder_y["Docs"] + FOLDER_H + 8, 220, 50))
    cells.append(vertex("noteLogs", "audit_log.py y logs/ son diseño,<br>pendientes de implementación<br>(RF-03/04/06 oficiales).",
                         NOTE, COL2_X, comp_y["AuditLog"] + COMP_H + 30, 220, 50))

    # Carriles explícitos para las aristas columna2 -> columna3, para que sus
    # etiquetas no se crucen entre sí cerca de models/ y voices/.
    gutter_lo = COL2_X + COL2_W + 15
    def lane(i):
        return gutter_lo + 24 * i
    def cy(box_y, h):
        return box_y + h / 2

    R = "exitX=1;exitY=0.5;"
    L = "entryX=0;entryY=0.5;"
    T = "entryX=0.5;entryY=0;"
    B = "exitX=0.5;exitY=1;"

    appy_cy = cy(comp_y["AppPy"], COMP_H)
    train_cy = cy(comp_y["TrainLstm"], COMP_H)
    audit_cy = cy(comp_y["AuditLog"], COMP_H)
    dataset_cy = cy(folder_y["Dataset"], FOLDER_H)
    models_cy = cy(folder_y["Models"], FOLDER_H)
    voices_cy = cy(folder_y["Voices"], FOLDER_H)
    logs_cy = cy(folder_y["Logs"], FOLDER_H)

    edges = [
        ("WebApp", "WebHooks", "usa", "exitX=0.3;exitY=1;", "entryX=0.5;entryY=0;", None, None),
        ("WebApp", "WebComponents", "usa", "exitX=0.7;exitY=1;", "entryX=0.5;entryY=0;", None, None),
        ("WebHooks", "WebLib", "usa", "exitX=0.3;exitY=1;", "entryX=0.2;entryY=0;", None, None),
        ("WebComponents", "WebLib", "usa", "exitX=0.7;exitY=1;", "entryX=0.8;entryY=0;", None, None),
        ("WebHooks", "AppPy", "HTTP / WS", R, "entryX=0;entryY=0.35;", None, None),
        ("WebComponents", "AppPy", "HTTP", R, "entryX=0;entryY=0.65;", None, None),
        ("AppPy", "SrcModel", "usa", "exitX=0;exitY=0.7;", "entryX=1;entryY=0.5;", None, None),
        ("AppPy", "CaptureVal", "usa", B, T, None, None),
        ("AppPy", "Dataset", "lee/escribe .npy", R, L, [(lane(0), appy_cy), (lane(0), dataset_cy)], None),
        ("AppPy", "Models", "lee pesos (.pth)", R, L, [(lane(1), appy_cy), (lane(1), models_cy)], None),
        ("AppPy", "Voices", "lee modelo Piper (.onnx)", R, L, [(lane(2), appy_cy), (lane(2), voices_cy)], None),
        ("TrainLstm", "Dataset", "lee muestras", R, L, [(lane(3), train_cy), (lane(3), dataset_cy)], None),
        ("TrainLstm", "SrcModel", "usa", "exitX=0;exitY=0.5;", "entryX=1;entryY=0.8;", None, None),
        ("TrainLstm", "Models", "escribe pesos", R, L, [(lane(4), train_cy), (lane(4), models_cy)], None),
        ("AppPy", "AuditLog", "usa (RF-04.1, diseñado)", B, T, None, None),
        ("AuditLog", "Logs", "escribe eventos/reportes\n(JSON Lines, diseñado)", R, L,
         [(lane(2), audit_cy), (lane(2), logs_cy)], None),
    ]
    for i, (s, t, label, ex, en, pts, lx) in enumerate(edges):
        cells.append(edge(f"e{i}", s, t, DEP, label, ex, en, pts, lx))

    xml = f'<mxfile><diagram name="Vista de Desarrollo"><mxGraphModel><root>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>'
    OUT.write_text(xml, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
