from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent

FILL = "#F5F7FA"
STROKE = "#1E448A"
CLS = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=" + FILL + ";strokeColor=" + STROKE + ";"
    "fontFamily=Helvetica;fontSize=14;verticalAlign=top;align=center;spacing=6;"
)
TITLE = "text;html=1;align=left;verticalAlign=middle;fontStyle=1;fontSize=15;fontFamily=Helvetica;"
EDGE = (
    "endArrow=none;html=1;strokeColor=#333333;fontFamily=Helvetica;fontSize=13;"
    "labelBackgroundColor=#FFFFFF;rounded=0;"
)
COMPOSITION = EDGE + "startArrow=diamondThin;startFill=1;startSize=14;"
MULT = (
    "edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];"
    "fontSize=13;fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;"
)

W = {"L": 195, "C": 175, "R": 195}
X = {"L": 0, "C": 300, "R": 580}
ROW = {0: 60, 1: 200, 2: 320, 3: 450, 4: 600}
LINE = 19


def box_h(header, attrs, stereo):
    return 14 + LINE * len(header) + (LINE * len(attrs) + 10 if attrs else 0) + (LINE if stereo else 0)


def class_html(header, attrs, stereo):
    parts = []
    if stereo:
        parts.append("<i>&#171;diseñado&#187;</i><br>")
    parts.append("<b>" + "<br>".join(escape(h) for h in header) + "</b>")
    if attrs:
        parts.append("<hr size='1' style='margin:4px 0'/>")
        parts.append("<div align='left'>" + "<br>".join(escape(a) for a in attrs) + "</div>")
    return "".join(parts)


def xml_vertex(cid, value, style, x, y, w, h, parent="1"):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def xml_edge(cid, label, style, points):
    (sx, sy), (tx, ty) = points[0], points[-1]
    mids = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points[1:-1])
    arr = f'<Array as="points">{mids}</Array>' if mids else ""
    return (f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry"><mxPoint x="{sx}" y="{sy}" as="sourcePoint"/>'
            f'<mxPoint x="{tx}" y="{ty}" as="targetPoint"/>{arr}</mxGeometry></mxCell>')


def xml_mult(cid, value, edge_id, pos, offset):
    return (f'<mxCell id="{cid}" value="{escape(value)}" style="{MULT}" vertex="1" connectable="0" parent="{edge_id}">'
            f'<mxGeometry x="{pos}" y="0" relative="1" as="geometry"><mxPoint x="{offset[0]}" y="{offset[1]}" as="offset"/></mxGeometry></mxCell>')


class Diagram:
    def __init__(self, title):
        self.title = title
        self.boxes = {}
        self.cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>',
                      xml_vertex("title", title, TITLE, 0, 0, 780, 30)]
        self.n = 0

    def cls(self, cid, col, row, header, attrs=(), stereo=False, dy=0, h=None):
        h = h or box_h(header, attrs, stereo)
        x, y, w = X[col], ROW[row] + dy, W[col]
        self.boxes[cid] = (x, y, w, h)
        self.cells.append(xml_vertex(cid, class_html(header, attrs, stereo), CLS, x, y, w, h))

    def at(self, cid, fx, fy):
        x, y, w, h = self.boxes[cid]
        return (x + w * fx, y + h * fy)

    def link(self, points, label, m_start, m_end, style=EDGE, m_off=(0, -11)):
        self.n += 1
        eid = f"e{self.n}"
        self.cells.append(xml_edge(eid, label, style, points))
        self.cells.append(xml_mult(f"{eid}s", m_start, eid, -0.8, m_off))
        self.cells.append(xml_mult(f"{eid}t", m_end, eid, 0.8, m_off))

    def h(self, a, b, label, ma, mb, y=None, style=EDGE):
        ax, ay, aw, ah = self.boxes[a]
        bx, by, bw, bh = self.boxes[b]
        y = y if y is not None else max(ay, by) + 16
        if ax < bx:
            pts = [(ax + aw, y), (bx, y)]
        else:
            pts = [(ax, y), (bx + bw, y)]
        self.link(pts, label, ma, mb, style)

    def v(self, a, b, label, ma, mb, x=None, style=EDGE):
        ax, ay, aw, ah = self.boxes[a]
        bx, by, bw, bh = self.boxes[b]
        x = x if x is not None else ax + aw / 2
        if ay < by:
            pts = [(x, ay + ah), (x, by)]
        else:
            pts = [(x, ay), (x, by + bh)]
        self.link(pts, label, ma, mb, style, m_off=(-14, 0))

    def write(self, name):
        body = "".join(self.cells)
        out = HERE / f"{name}.drawio"
        out.write_text(f'<mxfile><diagram name="{escape(self.title)}"><mxGraphModel><root>{body}</root>'
                       f'</mxGraphModel></diagram></mxfile>', encoding="utf-8")
        print(f"wrote {out}")


def vista_comunicacion():
    d = Diagram("Modelo de Dominio — LSA Salud (vista A: comunicación y atención)")
    d.cls("consent", "L", 0, ["ConsentimientoDeCámara"], ["otorgado", "marcaTemporal"])
    d.cls("paciente", "L", 1, ["Paciente"], h=56)
    d.cls("secuencia", "L", 2, ["SecuenciaDeSeñas"], ["estado", "marcaTemporalInicio"])
    d.cls("traduccion", "L", 3, ["Traducción"], ["textoOriginal", "textoTraducido", "fuente"])
    d.cls("plantilla", "L", 4, ["PlantillaMédica"], ["combinaciónDeSeñas", "fraseResultante"])
    d.cls("estacion", "C", 1, ["EstaciónDeAtención"], ["tipo"])
    d.cls("reporte", "C", 2, ["ReporteDeTraducción"], ["motivo", "marcaTemporal"])
    d.cls("mensaje", "C", 3, ["Mensaje"], ["texto", "rolEmisor", "horaEnvío"])
    d.cls("sintesis", "C", 4, ["SíntesisDeVoz"], ["voz", "formatoAudio"])
    d.cls("auditoria", "R", 0, ["EventoDeAuditoría"], ["tipoDeOperación", "marcaTemporal", "resultado"], dy=-10)
    d.cls("personal", "R", 1, ["Personal de Recepción", "o Enfermería"])
    d.cls("conversacion", "R", 3, ["Conversación"], ["fechaInicio"])

    px, py, pw, ph = d.boxes["paciente"]
    ex, ey, ew, eh = d.boxes["estacion"]
    rx, ry, rw, rh = d.boxes["reporte"]
    mx, my, mw, mh = d.boxes["mensaje"]
    sx, sy, sw, sh = d.boxes["personal"]
    ax, ay, aw, ah = d.boxes["auditoria"]
    cx, cy, cw, ch = d.boxes["conversacion"]

    d.v("paciente", "consent", "otorga", "1", "0..1")
    d.h("paciente", "estacion", "utiliza", "1", "1", y=py + 16)
    d.h("personal", "estacion", "utiliza", "1", "1", y=py + 16)
    d.v("paciente", "secuencia", "realiza", "1", "0..*")
    d.v("secuencia", "traduccion", "da origen a", "1", "0..1")
    d.v("traduccion", "plantilla", "puede basarse en", "0..*", "0..1")
    d.h("traduccion", "mensaje", "genera", "1", "1", y=my + 30)
    d.v("mensaje", "sintesis", "tiene", "1", "0..1")
    d.h("mensaje", "conversacion", "pertenece a", "0..*", "1", y=cy + 26)
    d.v("mensaje", "reporte", "puede tener", "1", "0..1")

    d.link([(ex + ew * 0.8, ey), (ex + ew * 0.8, ay + ah / 2), (ax, ay + ah / 2)],
           "origina", "1", "0..*")

    lane_top = 42
    lane_x = X["R"] + W["R"] + 30
    d.link([(ex + ew * 0.25, ey), (ex + ew * 0.25, lane_top), (lane_x, lane_top),
            (lane_x, cy + ch / 2), (cx + cw, cy + ch / 2)],
           "muestra", "2", "1")

    gap_lc = X["L"] + W["L"] + 50
    d.link([(px + pw, py + ph - 6), (gap_lc, py + ph - 6), (gap_lc, ry + rh / 2), (rx, ry + rh / 2)],
           "señala", "1", "0..*")

    gap_cr = X["C"] + W["C"] + 55
    d.link([(sx, sy + sh - 8), (gap_cr, sy + sh - 8), (gap_cr, ry + rh / 2), (rx + rw, ry + rh / 2)],
           "señala", "1", "0..*")

    y_gap = (ry + rh + my) / 2
    d.link([(sx + sw / 2, sy + sh), (sx + sw / 2, y_gap), (mx + mw * 0.85, y_gap), (mx + mw * 0.85, my)],
           "redacta", "1", "0..*")

    d.write("01_modelo_dominio_a")


def vista_reconocimiento():
    d = Diagram("Modelo de Dominio — LSA Salud (vista B: reconocimiento y gestión del modelo)")
    d.cls("paciente", "L", 0, ["Paciente"])
    d.cls("secuencia", "L", 1, ["SecuenciaDeSeñas"], ["estado", "marcaTemporalInicio"])
    d.cls("palabra", "L", 2, ["PalabraReconocida"], ["confianza", "posición", "marcaTemporal"], dy=50)
    d.cls("clase", "L", 4, ["ClaseDeSeña"], ["nombre"], dy=40)
    d.cls("modelo", "C", 2, ["ModeloDe", "Reconocimiento"], ["versión", "cantidadDeClases", "exactitudDeValidación"], dy=50)
    d.cls("dev", "R", 2, ["Desarrollador de IA /", "Equipo de Proyecto"], dy=50)
    d.cls("muestra", "R", 4, ["MuestraDe", "Entrenamiento"], ["cantidadDeFrames", "fechaCaptura", "modoDeCaptura"], dy=40)

    wx, wy, ww, wh = d.boxes["palabra"]
    ox, oy, ow, oh = d.boxes["modelo"]
    kx, ky, kw, kh = d.boxes["clase"]

    d.v("paciente", "secuencia", "realiza", "1", "0..*")
    d.v("secuencia", "palabra", "compuesta por", "1", "1..*", style=COMPOSITION)
    d.v("palabra", "clase", "corresponde a", "0..*", "1")
    d.h("modelo", "palabra", "clasifica", "1", "0..*", y=wy + 30)
    d.h("dev", "modelo", "entrena", "1", "0..*", y=wy + 30)
    d.v("dev", "muestra", "captura", "1", "0..*")
    d.h("muestra", "clase", "ejemplifica", "0..*", "1", y=ky + 26)
    y_gap = oy + oh + 40
    d.link([(ox + ow * 0.5, oy + oh), (ox + ow * 0.5, y_gap), (kx + kw * 0.8, y_gap), (kx + kw * 0.8, ky)],
           "reconoce", "1", "1..*")

    d.write("01_modelo_dominio_b")


if __name__ == "__main__":
    vista_comunicacion()
    vista_reconocimiento()
