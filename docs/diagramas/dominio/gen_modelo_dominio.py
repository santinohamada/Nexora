"""Genera 01_modelo_dominio.drawio: Modelo de Dominio de LSA Salud (Larman),
en una cuadricula angosta de 3 columnas para que el PDF exportado quede en
formato retrato/portrait (en vez del layout ancho que producia PlantUML/smetana
para este grafo muy interconectado; ver docs/render.sh y la guia de figuras).

Mismos elementos, atributos, asociaciones (con nombre y multiplicidad en
ambos extremos) y reglas de Larman (sin metodos, sin tipos) que el .puml
original que reemplaza. Cada asociación se enruta explícitamente por un
"carril" propio dentro del corredor entre columnas para que las líneas y
las etiquetas no se superpongan (layout, no semántica).
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).with_name("01_modelo_dominio.drawio")

FILL = "#F5F7FA"
STROKE = "#1E448A"
CLS = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=" + FILL + ";strokeColor=" + STROKE + ";"
    "fontFamily=Helvetica;fontSize=13;verticalAlign=top;align=center;spacing=6;"
)
TITLE = "text;html=1;align=left;verticalAlign=middle;fontStyle=1;fontSize=15;fontFamily=Helvetica;"
ASSOC = (
    "endArrow=none;startArrow=none;html=1;strokeColor=#333333;fontFamily=Helvetica;"
    "fontSize=12;labelBackgroundColor=#FFFFFF;edgeStyle=orthogonalEdgeStyle;rounded=0;"
)
COMPOSITION = (
    "endArrow=none;startArrow=diamondThin;startFill=1;startSize=14;html=1;"
    "strokeColor=#333333;fontFamily=Helvetica;fontSize=12;labelBackgroundColor=#FFFFFF;"
    "edgeStyle=orthogonalEdgeStyle;rounded=0;"
)
MULT_STYLE = (
    "edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];"
    "fontSize=11;fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;"
)

GAP_X = 130
GAP_Y = 24
TOP = 44
COL_W = {1: 200, 2: 200, 3: 230}
COL_X = {1: 0, 2: COL_W[1] + GAP_X, 3: COL_W[1] + GAP_X + COL_W[2] + GAP_X}
GUTTER1 = (COL_X[1] + COL_W[1], COL_X[2])  # entre columna 1 y 2
GUTTER2 = (COL_X[2] + COL_W[2], COL_X[3])  # entre columna 2 y 3

# (id, columna, header (lista de lineas), atributos, alto, estereotipo?)
CLASSES = [
    ("Paciente", 1, ["Paciente"], [], 34, False),
    ("Personal", 1, ["Personal de Recepción", "o Enfermería"], [], 50, False),
    ("EstaciónDeAtención", 1, ["EstaciónDeAtención"], ["tipo"], 54, False),
    ("ConsentimientoDeCámara", 1, ["ConsentimientoDeCámara"], ["otorgado", "marcaTemporal"], 68, False),
    ("ReporteDeTraducción", 1, ["ReporteDeTraducción"], ["motivo", "marcaTemporal"], 68, False),
    ("Mensaje", 1, ["Mensaje"], ["texto", "rolEmisor", "horaEnvío"], 84, False),

    ("SecuenciaDeSeñas", 2, ["SecuenciaDeSeñas"], ["estado", "marcaTemporalInicio"], 68, False),
    ("PalabraReconocida", 2, ["PalabraReconocida"], ["confianza", "posición", "marcaTemporal"], 84, False),
    ("ClaseDeSeña", 2, ["ClaseDeSeña"], ["nombre"], 54, False),
    ("Traducción", 2, ["Traducción"], ["textoOriginal", "textoTraducido", "fuente"], 84, False),
    ("PlantillaMedica", 2, ["PlantillaMédica"], ["combinaciónDeSeñas", "fraseResultante"], 68, False),
    ("SíntesisDeVoz", 2, ["SíntesisDeVoz"], ["voz", "formatoAudio"], 68, False),

    ("DevIA", 3, ["Desarrollador de IA /", "Equipo de Proyecto"], [], 50, False),
    ("ModeloDeReconocimiento", 3, ["ModeloDeReconocimiento"], ["versión", "cantidadDeClases", "exactitudDeValidación"], 100, False),
    ("MuestraDeEntrenamiento", 3, ["MuestraDeEntrenamiento"], ["cantidadDeFrames", "fechaCaptura", "modoDeCaptura"], 100, False),
    ("EventoDeAuditoría", 3, ["EventoDeAuditoría"], ["tipoDeOperación", "marcaTemporal", "resultado"], 100, True),
    ("Conversación", 3, ["Conversación"], ["fechaInicio"], 54, False),
]

# (source, target, label, mult_src, mult_tgt, composition?, ruta)
# ruta: "straight" (misma columna, sin caja entre medio) | "loop1"/"loop2L" (misma
# columna con caja entre medio: rodea por el corredor 1 o 2) | "lane1"/"lane2"
# (columnas adyacentes: cruza por el corredor 1 o 2) | "detour" (columna 1<->3:
# rodea por debajo de toda la cuadrícula, ver DETOUR_Y).
ASSOCIATIONS = [
    ("Paciente", "EstaciónDeAtención", "utiliza >", "1", "1", False, "loop1"),
    ("Personal", "EstaciónDeAtención", "utiliza >", "1", "1", False, "straight"),
    ("EstaciónDeAtención", "Conversación", "muestra >", "2", "1", False, "detour"),
    ("EstaciónDeAtención", "EventoDeAuditoría", "origina >", "1", "0..*", False, "detour"),
    ("Paciente", "ConsentimientoDeCámara", "otorga >", "1", "0..1", False, "loop1"),
    ("Paciente", "SecuenciaDeSeñas", "realiza >", "1", "0..*", False, "lane1"),
    ("SecuenciaDeSeñas", "PalabraReconocida", "compuesta por >", "1", "1..*", True, "straight"),
    ("PalabraReconocida", "ClaseDeSeña", "corresponde a >", "0..*", "1", False, "straight"),
    ("SecuenciaDeSeñas", "Traducción", "da origen a >", "1", "0..1", False, "loop2"),
    ("Traducción", "PlantillaMedica", "puede basarse en >", "0..*", "0..1", False, "straight"),
    ("Traducción", "Mensaje", "genera >", "1", "1", False, "lane1"),
    ("Mensaje", "SíntesisDeVoz", "tiene >", "1", "0..1", False, "lane1"),
    ("Mensaje", "Conversación", "pertenece a >", "0..*", "1", False, "detour"),
    ("Mensaje", "ReporteDeTraducción", "puede tener >", "1", "0..1", False, "straight"),
    ("Paciente", "ReporteDeTraducción", "señala >", "1", "0..*", False, "loop1"),
    ("Personal", "ReporteDeTraducción", "señala >", "1", "0..*", False, "loop1"),
    ("Personal", "Mensaje", "redacta >", "1", "0..*", False, "loop1"),
    ("DevIA", "MuestraDeEntrenamiento", "captura >", "1", "0..*", False, "loop2L"),
    ("MuestraDeEntrenamiento", "ClaseDeSeña", "ejemplifica >", "0..*", "1", False, "lane2"),
    ("DevIA", "ModeloDeReconocimiento", "entrena >", "1", "0..*", False, "straight"),
    ("ModeloDeReconocimiento", "ClaseDeSeña", "reconoce >", "1", "1..*", False, "lane2"),
    ("ModeloDeReconocimiento", "PalabraReconocida", "clasifica >", "1", "0..*", False, "lane2"),
]

# Índices (0-based) de asociaciones columna1<->columna3: se desvían por
# debajo de toda la cuadrícula para no atravesar cajas de la columna 2.
DETOUR_Y = {2: 700, 3: 685, 12: 715}

COL_OF = {cid: col for (cid, col, *_rest) in CLASSES}


def vertex(cid, value, style, x, y, w, h, parent="1"):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def edge(cid, s, t, style, value, points=None, parent="1"):
    pts = ""
    if points:
        pts = "<Array as=\"points\">" + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" edge="1" parent="{parent}" source="{s}" target="{t}">'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>')


def edge_label(cid, parent_edge, value, x):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{MULT_STYLE}" vertex="1" connectable="0" parent="{parent_edge}">'
            f'<mxGeometry x="{x}" y="0" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry></mxCell>')


def class_html(header_lines, attrs, stereotype):
    parts = []
    if stereotype:
        parts.append("<font style='font-style:italic'>&#171;diseñado&#187;</font><br>")
    parts.append("<b>" + "<br>".join(escape(h) for h in header_lines) + "</b>")
    if attrs:
        parts.append("<hr size='1' style='margin:3px 0'/>")
        parts.append("<div align='left'>" + "<br>".join(escape(a) for a in attrs) + "</div>")
    return "".join(parts)


def build():
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(vertex("title", "Modelo de Dominio — LSA Salud", TITLE, 0, 0, 500, 30))

    col_y = {1: TOP, 2: TOP, 3: TOP}
    positions = {}
    for cid, col, header, attrs, h, stereo in CLASSES:
        w = COL_W[col]
        x = COL_X[col]
        y = col_y[col]
        value = class_html(header, attrs, stereo)
        cells.append(vertex(cid, value, CLS, x, y, w, h))
        positions[cid] = (x, y, w, h)
        col_y[col] = y + h + GAP_Y

    def mid(cid):
        x, y, w, h = positions[cid]
        return x + w / 2, y + h / 2, x, y, w, h

    # --- Paso 1: para cada asociación, decidir qué lado de cada caja usa ---
    # (R=derecha, L=izquierda, T=arriba, B=abajo), para poder repartir varias
    # aristas que tocan el mismo lado de la misma caja en puntos distintos
    # (si no, todas saldrían del mismo pixel y las etiquetas se superpondrían).
    side_of = {}  # eid -> (source_side, target_side)
    for i, (s, t, label, ms, mt, comp, route) in enumerate(ASSOCIATIONS):
        if route == "straight":
            sy0, ty0 = positions[s][1], positions[t][1]
            side_of[i] = ("B", "T") if sy0 < ty0 else ("T", "B")
        elif route in ("loop1",):
            side_of[i] = ("R", "R")
        elif route in ("loop2", "loop2L"):
            side_of[i] = ("L", "L") if route == "loop2L" else ("R", "R")
        elif route in ("lane1", "lane2"):
            side_of[i] = ("R", "L") if COL_OF[s] < COL_OF[t] else ("L", "R")
        elif route == "detour":
            side_of[i] = ("B", "B")

    slot_count = {}
    for i, (s, t, *_r) in enumerate(ASSOCIATIONS):
        ss, ts = side_of[i]
        slot_count[(s, ss)] = slot_count.get((s, ss), 0) + 1
        slot_count[(t, ts)] = slot_count.get((t, ts), 0) + 1
    slot_seen = {}

    def frac(box, side):
        n = slot_count[(box, side)]
        k = slot_seen.get((box, side), 0)
        slot_seen[(box, side)] = k + 1
        if n == 1:
            return 0.5
        return round(0.22 + 0.56 * k / (n - 1), 3)

    lane_n = {"lane1": 0, "loop1": 0, "lane2": 0, "loop2": 0, "loop2L": 0}
    LANE_STEP = 16
    g1_lo, _ = GUTTER1
    g2_lo, _ = GUTTER2
    XY = {"R": (1, None), "L": (0, None), "T": (None, 0), "B": (None, 1)}

    for i, (s, t, label, ms, mt, comp, route) in enumerate(ASSOCIATIONS):
        eid = f"e{i}"
        base_style = COMPOSITION if comp else ASSOC
        ss, ts = side_of[i]
        sfx, sfy = XY[ss]
        tfx, tfy = XY[ts]
        sFrac = frac(s, ss)
        tFrac = frac(t, ts)
        ex = sfx if sfx is not None else sFrac
        ey = sfy if sfy is not None else sFrac
        en = tfx if tfx is not None else tFrac
        ev = tfy if tfy is not None else tFrac
        sx0, sy0, sw, sh = positions[s]
        tx0, ty0, tw, th = positions[t]
        s_pt = (sx0 + (sw if ss == "R" else 0 if ss == "L" else sw * sFrac),
                sy0 + (sh if ss == "B" else 0 if ss == "T" else sh * sFrac))
        t_pt = (tx0 + (tw if ts == "R" else 0 if ts == "L" else tw * tFrac),
                ty0 + (th if ts == "B" else 0 if ts == "T" else th * tFrac))

        style = base_style + f"exitX={ex};exitY={ey};entryX={en};entryY={ev};"
        points = None

        if route == "straight":
            pass
        elif route in ("loop1", "loop2", "loop2L"):
            key = route
            gutter_lo = g1_lo if route == "loop1" else g2_lo
            lane_x = gutter_lo + 20 + lane_n[key] * LANE_STEP
            lane_n[key] += 1
            points = [(lane_x, s_pt[1]), (lane_x, t_pt[1])]
        elif route in ("lane1", "lane2"):
            key = route
            gutter_lo = g1_lo if route == "lane1" else g2_lo
            lane_x = gutter_lo + 20 + lane_n[key] * LANE_STEP
            lane_n[key] += 1
            points = [(lane_x, s_pt[1]), (lane_x, t_pt[1])]
        elif route == "detour":
            y_lane = DETOUR_Y[i]
            points = [(s_pt[0], y_lane), (t_pt[0], y_lane)]
        else:
            raise ValueError(route)

        cells.append(edge(eid, s, t, style, label, points))
        cells.append(edge_label(f"{eid}ms", eid, ms, -0.88))
        cells.append(edge_label(f"{eid}mt", eid, mt, 0.88))

    max_y = max([y + h for (x, y, w, h) in positions.values()] + list(DETOUR_Y.values()))
    width = COL_X[3] + COL_W[3]
    height = max_y + 15
    print(f"estimated canvas: {width} x {height} (AR={height/width:.3f})")

    xml = f'<mxfile><diagram name="Modelo de Dominio"><mxGraphModel><root>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>'
    OUT.write_text(xml, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
