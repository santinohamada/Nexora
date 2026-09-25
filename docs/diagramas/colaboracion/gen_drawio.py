"""gen_drawio.py — genera los 9 diagramas de colaboracion UML (DC-01..DC-09)
como archivos .drawio editables, con notacion Larman/UML 2.5 estricta.
DC-06, DC-07 y DC-08 cubren RF-03, RF-04 y RF-06 respectivamente;
DC-09 cubre RNF-03:

- objetos como rectangulos con nombre subrayado (instancia : Clase o :Clase)
- UN enlace sin flecha entre cada par de objetos que colabora, SIEMPRE
  horizontal o vertical (nunca diagonal); cuando dos objetos no comparten
  fila/columna el enlace es una polilinea ortogonal (uno o dos quiebres)
- cada mensaje es una flechita corta y propia, paralela al segmento del
  enlace al que pertenece, apuntando al receptor, con su numero jerarquico
  (1, 1.1, 2.1.3...); la etiqueta va SIEMPRE del lado lejano de la flechita
  (nunca puede pisar la flecha ni el enlace: su borde cercano arranca
  despues del offset de la flecha)
- varios mensajes entre el mismo par se apilan alejandose cada vez mas del
  enlace (el espacio de apilado se calcula segun el alto/ancho real de cada
  etiqueta, incluyendo las que envuelven a 2 lineas); los de direccion
  opuesta van al otro lado del enlace
- automensajes: bucle rectangular real y visible sobre el propio objeto,
  del lado que esta libre de otros enlaces
- notas: se ubican pegadas al objeto, del lado libre, con conector corto
  que no cruza ningun otro objeto

Uso: C:\\Nexora\\venv\\Scripts\\python.exe gen_drawio.py
Escribe docs/diagramas/colaboracion/08_colaboracion_dc0N.drawio (N=1..9).
"""
from __future__ import annotations

import html
import os
from dataclasses import dataclass, field

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

OBJ_STYLE = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;"
    "fontFamily=Helvetica;fontSize=14;align=center;verticalAlign=middle;"
)
LINK_STYLE = "endArrow=none;startArrow=none;html=1;strokeColor=#000000;strokeWidth=1;rounded=0;"
MSG_STYLE = "endArrow=block;startArrow=none;endFill=1;endSize=8;html=1;strokeColor=#000000;strokeWidth=1;rounded=0;"
NOTE_STYLE = (
    "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;"
    "align=center;verticalAlign=middle;fontFamily=Helvetica;fontSize=11;"
    "fillColor=#FFF8DC;strokeColor=#B8860B;size=14;"
)
NOTE_LINK_STYLE = "endArrow=none;startArrow=none;dashed=1;html=1;strokeColor=#B8860B;"

# geometry constants (px)
ARROW_OFFSET = 20      # distance from the link to the first (closest) arrow
ARROW_LABEL_GAP = 14   # gap between an arrow's centerline and its label's near edge
                        # (ARROW_OFFSET+ARROW_LABEL_GAP=34 must exceed half the
                        # height of any object with a horizontal-link message
                        # stacked above/below it, so the label clears the box;
                        # keep those objects' height <= 64px)
NEXT_ARROW_GAP = 12    # gap between a label's far edge and the next stacked arrow
SEG_LEN = 34           # length of each message arrow
T_AB = 0.42            # along-segment position for a->b messages
T_BA = 0.58            # along-segment position for b->a messages


def esc(s: str) -> str:
    return html.escape(s, quote=True)


@dataclass
class Obj:
    id: str
    label: str
    x: float
    y: float
    w: float = 190
    h: float = 46

    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)


@dataclass
class Msg:
    num: str
    text: str
    direction: str  # 'ab' (a->b) or 'ba' (b->a)
    seg: int = 0     # which segment of the (possibly bent) link hosts this message


@dataclass
class Link:
    a: str
    b: str
    messages: list = field(default_factory=list)
    self_loop: bool = False
    self_side: str = "top"       # 'top' | 'bottom' | 'left' | 'right'
    self_frac: tuple = (0.60, 0.88)  # where along that side the loop sits
    waypoints: list = field(default_factory=list)  # intermediate bend points (x, y)
    a_exit: tuple = None  # explicit (side, frac) exit point on A's border, bypassing border_point
    b_entry: tuple = None  # explicit (side, frac) entry point on B's border


@dataclass
class Note:
    target: str
    x: float
    y: float
    text: str
    w: float = 210
    h: float = 64


@dataclass
class Diagram:
    name: str
    title: str
    objects: list
    links: list
    notes: list = field(default_factory=list)
    title_pos: tuple = (40, 0)
    title_w: float = 900


class IdGen:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return f"c{self.n}"


def border_point(box: Obj, toward):
    """Point on box's border in the direction of `toward` (a point outside it)."""
    cx, cy = box.center()
    dx = toward[0] - cx
    dy = toward[1] - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    hw, hh = box.w / 2, box.h / 2
    candidates = []
    if dx != 0:
        candidates.append(abs(hw / dx))
    if dy != 0:
        candidates.append(abs(hh / dy))
    scale = min(candidates) if candidates else 0
    return (cx + dx * scale, cy + dy * scale)


def side_point(box: Obj, side: str, frac: float):
    """Explicit point on a specific border side, at fraction `frac` along it.
    Used for bent links where the exit must land at an exact off-center
    spot (so the adjoining segment is guaranteed axis-aligned), instead of
    the direction-toward-target math in border_point (which only produces
    an axis-aligned segment when the target shares x or y with the box's
    own center)."""
    if side == "top":
        return (box.x + box.w * frac, box.y)
    if side == "bottom":
        return (box.x + box.w * frac, box.y + box.h)
    if side == "left":
        return (box.x, box.y + box.h * frac)
    return (box.x + box.w, box.y + box.h * frac)  # right


def vertex_xml(id_, value, x, y, w, h, style):
    return (
        f'<mxCell id="{id_}" value="{esc(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" as="geometry"/>'
        f"</mxCell>"
    )


def polyline_edge_xml(id_, points, style):
    p0, pN = points[0], points[-1]
    mid = points[1:-1]
    mid_xml = "".join(f'<mxPoint x="{p[0]:.1f}" y="{p[1]:.1f}"/>' for p in mid)
    points_block = f'<Array as="points">{mid_xml}</Array>' if mid else ""
    return (
        f'<mxCell id="{id_}" style="{style}" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{p0[0]:.1f}" y="{p0[1]:.1f}" as="sourcePoint"/>'
        f'<mxPoint x="{pN[0]:.1f}" y="{pN[1]:.1f}" as="targetPoint"/>'
        f"{points_block}"
        f"</mxGeometry></mxCell>"
    )


def text_xml(id_, text, x, y, w, h, align="center"):
    style = (
        f"text;html=1;align={align};verticalAlign=middle;fontFamily=Helvetica;"
        f"fontSize=13;whiteSpace=wrap;"
    )
    return vertex_xml(id_, text, x, y, w, h, style)


def label_size(text: str, base_w=190):
    two_line = len(text) > 26
    if two_line:
        w = min(230, base_w + 30)
        h = 42
    else:
        # size to the actual text so short labels don't needlessly extend
        # a stacked lane far past nearby objects/links
        w = min(base_w, max(72, len(text) * 7.0 + 14))
        h = 20
    return w, h


# ---------------------------------------------------------------------------
# link / message geometry
# ---------------------------------------------------------------------------
def build_link_cells(link: Link, objs, idg: IdGen):
    cells = []
    A = objs[link.a]

    if link.self_loop:
        return build_self_loop_cells(link, A, idg)

    B = objs[link.b]
    if link.a_exit:
        a_pt = side_point(A, *link.a_exit)
    else:
        first_target = link.waypoints[0] if link.waypoints else B.center()
        a_pt = border_point(A, first_target)
    if link.b_entry:
        b_pt = side_point(B, *link.b_entry)
    else:
        last_target = link.waypoints[-1] if link.waypoints else A.center()
        b_pt = border_point(B, last_target)
    points = [a_pt, *link.waypoints, b_pt]
    cells.append(polyline_edge_xml(idg(), points, LINK_STYLE))

    n_seg = len(points) - 1
    by_seg = {i: {"ab": [], "ba": []} for i in range(n_seg)}
    for m in link.messages:
        seg_idx = min(max(m.seg, 0), n_seg - 1)
        by_seg[seg_idx][m.direction].append(m)

    for seg_idx in range(n_seg):
        p1, p2 = points[seg_idx], points[seg_idx + 1]
        for direction, msgs in by_seg[seg_idx].items():
            if not msgs:
                continue
            cells.extend(place_messages_on_segment(p1, p2, direction, msgs, idg))
    return cells


def place_messages_on_segment(p1, p2, direction, msgs, idg: IdGen):
    """Stack `msgs` (all same direction) perpendicular to segment p1->p2,
    each arrow+label placed strictly farther out than the previous one so
    nothing ever overlaps the link, the arrow, or another label."""
    cells = []
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    is_horizontal = abs(dy) < abs(dx)  # segment runs mostly left-right
    # unit direction along the segment (for the arrow's own heading)
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / length, dy / length
    # canonical perpendicular: a FIXED side regardless of which way the
    # segment happens to run (p1->p2 vs p2->p1), so 'ab' always renders on
    # the same visual side (above / right) and 'ba' on the other (below /
    # left) — using (-uy, ux) here would flip sign depending on segment
    # direction and made labels land back on top of the link.
    if is_horizontal:
        px, py = 0.0, -1.0  # positive offset = above the link
    else:
        px, py = 1.0, 0.0  # positive offset = right of the link

    sign = 1 if direction == "ab" else -1
    t = T_AB if direction == "ab" else T_BA
    base = (p1[0] + dx * t, p1[1] + dy * t)
    if direction == "ab":
        sdx, sdy = ux, uy
    else:
        sdx, sdy = -ux, -uy

    running = ARROW_OFFSET
    along = 0.0
    for m in msgs:
        arrow_off = running
        acx = base[0] + px * arrow_off * sign
        acy = base[1] + py * arrow_off * sign + along
        start = (acx - sdx * SEG_LEN / 2, acy - sdy * SEG_LEN / 2)
        end = (acx + sdx * SEG_LEN / 2, acy + sdy * SEG_LEN / 2)
        cells.append(polyline_edge_xml(idg(), [start, end], MSG_STYLE))

        text = f"{m.num}: {m.text}"
        w, h = label_size(text)
        label_near = arrow_off + ARROW_LABEL_GAP

        if is_horizontal:
            # perpendicular is vertical: label sits above (sign>0) or below (sign<0)
            label_center_off = label_near + h / 2
            lcx = base[0] + px * label_center_off * sign
            lcy = base[1] + py * label_center_off * sign
            cells.append(text_xml(idg(), text, lcx - w / 2, lcy - h / 2, w, h, align="center"))
            running = label_near + h + NEXT_ARROW_GAP
        else:
            # perpendicular is horizontal: label sits right (sign>0) or left (sign<0)
            link_x = base[0]
            box_y = acy - h / 2
            if sign > 0:
                box_x = link_x + label_near
                align = "left"
            else:
                box_x = link_x - label_near - w
                align = "right"
            cells.append(text_xml(idg(), text, box_x, box_y, w, h, align=align))
            along += max(h, SEG_LEN) + NEXT_ARROW_GAP
    return cells


# ---------------------------------------------------------------------------
# self-messages: a real, visible rectangular loop on a free side of the box
# ---------------------------------------------------------------------------
def build_self_loop_cells(link: Link, A: Obj, idg: IdGen):
    cells = []
    side = link.self_side
    f0, f1 = link.self_frac
    fm = (f0 + f1) / 2
    bump = 26

    if side == "top":
        x0, x1 = A.x + A.w * f0, A.x + A.w * f1
        y_edge, y_out = A.y, A.y - bump
        p0, p1, p2, p3 = (x0, y_edge), (x0, y_out), (x1, y_out), (x1, y_edge)
        label_anchor = (x0 - 8, y_out)
        label_align, stack_dir = "right", (0, -1)
    elif side == "bottom":
        x0, x1 = A.x + A.w * f0, A.x + A.w * f1
        y_edge, y_out = A.y + A.h, A.y + A.h + bump
        p0, p1, p2, p3 = (x0, y_edge), (x0, y_out), (x1, y_out), (x1, y_edge)
        label_anchor = (A.x + A.w * fm, y_out + 14)
        label_align, stack_dir = "center", (0, 1)
    elif side == "right":
        y0, y1 = A.y + A.h * f0, A.y + A.h * f1
        x_edge, x_out = A.x + A.w, A.x + A.w + bump
        p0, p1, p2, p3 = (x_edge, y0), (x_out, y0), (x_out, y1), (x_edge, y1)
        label_anchor = (x_out + 10, A.y + A.h * fm)
        label_align, stack_dir = "left", (0, 1)
    else:  # left
        y0, y1 = A.y + A.h * f0, A.y + A.h * f1
        x_edge, x_out = A.x, A.x - bump
        p0, p1, p2, p3 = (x_edge, y0), (x_out, y0), (x_out, y1), (x_edge, y1)
        label_anchor = (x_out - 10, A.y + A.h * fm)
        label_align, stack_dir = "right", (0, 1)

    cells.append(polyline_edge_xml(idg(), [p0, p1, p2, p3], MSG_STYLE))

    lx, ly = label_anchor
    step = 24
    for i, m in enumerate(link.messages):
        text = f"{m.num}: {m.text}"
        w, h = label_size(text, base_w=220)
        cx = lx + stack_dir[0] * i * step
        cy = ly + stack_dir[1] * i * step
        if label_align == "center":
            box_x, box_y = cx - w / 2, cy - h / 2
        elif label_align == "left":
            box_x, box_y = cx, cy - h / 2
        else:
            box_x, box_y = cx - w, cy - h / 2
        cells.append(text_xml(idg(), text, box_x, box_y, w, h, align=label_align))
    return cells


# ---------------------------------------------------------------------------
# notes
# ---------------------------------------------------------------------------
def build_note_cells(note: Note, objs, idg: IdGen):
    cells = []
    cells.append(vertex_xml(idg(), note.text, note.x, note.y, note.w, note.h, NOTE_STYLE))
    A = objs[note.target]
    note_c = (note.x + note.w / 2, note.y + note.h / 2)
    a_pt = border_point(A, note_c)
    n_pt = border_point(Obj("n", "", note.x, note.y, note.w, note.h), A.center())
    cells.append(polyline_edge_xml(idg(), [a_pt, n_pt], NOTE_LINK_STYLE))
    return cells


TITLE_CLEARANCE = 150


def render(diagram: Diagram) -> str:
    idg = IdGen()
    objs = {}
    body = []

    tx, ty = diagram.title_pos
    ty = max(ty, min(o.y for o in diagram.objects) - TITLE_CLEARANCE)
    body.append(
        vertex_xml(
            idg(),
            diagram.title,
            tx,
            ty,
            diagram.title_w,
            30,
            "text;html=1;align=left;verticalAlign=middle;fontFamily=Helvetica;"
            "fontSize=15;fontStyle=1;whiteSpace=wrap;",
        )
    )

    for o in diagram.objects:
        objs[o.id] = o
        body.append(vertex_xml(idg(), f"<u>{esc(o.label)}</u>", o.x, o.y, o.w, o.h, OBJ_STYLE))

    for link in diagram.links:
        body.extend(build_link_cells(link, objs, idg))

    for note in diagram.notes:
        body.extend(build_note_cells(note, objs, idg))

    max_x = max((o.x + o.w for o in diagram.objects), default=1200) + 80
    max_y = max((o.y + o.h for o in diagram.objects), default=800) + 120

    xml = (
        '<mxfile host="app.diagrams.net">'
        f'<diagram id="{diagram.name}" name="{diagram.name}">'
        f'<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="{max_x:.0f}" pageHeight="{max_y:.0f}" math="0" shadow="0">'
        '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
        + "".join(body)
        + "</root></mxGraphModel></diagram></mxfile>"
    )
    return xml


# ---------------------------------------------------------------------------
# DC-01 — reconocerSeña(frame) — realiza CU-01
#
# compact grid (~690 px wide): mp above page (straight V), buf reached from
# page via a 4-point bend that swings right of mp then down, well clear of
# the mp-page message; page/ws/backend form a tight straight-H row; builder
# straight V under page, lstm straight V under backend (its long message
# is the diagram's rightmost extent); top3 reached from page's south border
# via a bend routed through page's own left edge (x=10), clear of the
# page-builder stacked labels (which sit at x~68-250).
# ---------------------------------------------------------------------------
def dc01() -> Diagram:
    objects = [
        Obj("mp", ":useMediaPipe", 290, 60, 170, 56),
        Obj("buf", "recordedFrames :\nPacientePage (buffer)", 0, 240, 160, 70),
        Obj("page", "handleFrame :\nPacientePage", 290, 200, 170, 150),
        Obj("builder", "useSentenceBuilder", 660, 239, 160, 56),
        Obj("top3", "TopPredictions", 660, 307, 160, 56),
        Obj("ws", "useSignWebSocket", 290, 470, 170, 56),
        Obj("backend", "websocket_predict :\napp.py", 290, 650, 170, 64),
        Obj("lstm", "model :\nSignLanguageLSTM", 290, 860, 170, 64),
    ]
    links = [
        Link("mp", "page", [Msg("1", "onFrame(frame)", "ab")]),
        Link("page", "buf", [Msg("1.1", "push(frame)", "ab")], a_exit=("left", 0.5), b_entry=("right", 0.5)),
        Link(
            "page",
            "builder",
            [Msg("1.2", "onFrameTick(frame)", "ab"), Msg("2.2.2", "addWord(sign)", "ab")],
            a_exit=("right", 0.45),
            b_entry=("left", 0.5),
        ),
        Link("page", "top3", [Msg("2.2.1", "actualizarDOM(top3)", "ab")], a_exit=("right", 0.9), b_entry=("left", 0.5)),
        Link("page", "ws", [Msg("2", "sendFrames(buffer)", "ab"), Msg("2.2", "onMessage(prediction)", "ba")]),
        Link(
            "ws",
            "backend",
            [Msg("2.1", "frames", "ab"), Msg("2.1.3", "enviarPrediccion({sign, confidence, top3})", "ba")],
        ),
        Link("backend", "backend", [Msg("2.1.1", "data := _prepare_input(data)", "ab")], self_loop=True, self_side="right"),
        Link("backend", "lstm", [Msg("2.1.2", "logits := model(input_tensor)", "ab")]),
    ]
    notes = [
        Note(
            "mp",
            520,
            56,
            "Extrae landmarks de manos, pose<br>y rostro (blendshapes) en cada<br>frame mediante MediaPipe.",
            230,
            64,
        )
    ]
    return Diagram(
        "08_colaboracion_dc01",
        "DC-01 — reconocerSeña(frame) — realiza CU-01",
        objects,
        links,
        notes,
        title_w=650,
    )


def dc02() -> Diagram:
    objects = [
        Obj("chat", "useChatChannel (Paciente)", 0, 60, 190, 56),
        Obj("builder", "useSentenceBuilder", 0, 230, 190, 56),
        Obj("backend", "process_sentence :\napp.py", 0, 420, 190, 340),
        Obj("templates", "MEDICAL_TEMPLATES", 460, 419, 190, 56),
        Obj("cache", "_translation_cache", 460, 494, 190, 56),
        Obj("ollama", "Ollama (qwen2:1.5b)", 0, 960, 190, 56),
    ]
    links = [
        Link("builder", "chat", [Msg("2", "sendMessage(mensaje)", "ab")]),
        Link("builder", "backend", [Msg("1", "POST /process_sentence({words})", "ab")]),
        Link(
            "backend",
            "templates",
            [Msg("1.2", "frase := _match_template(words)", "ab")],
            a_exit=("right", 0.08),
            b_entry=("left", 0.5),
        ),
        Link(
            "cache",
            "backend",
            [Msg("1.3", "traduccion := _cache_get(clave)", "ba"), Msg("1.5", "_cache_put(clave, oracion)", "ba")],
            a_exit=("left", 0.5),
            b_entry=("right", 0.3),
        ),
        Link(
            "backend",
            "backend",
            [Msg("1.1", "words := _normalize_words(words)", "ab")],
            self_loop=True,
            self_side="right",
            self_frac=(0.86, 0.97),
        ),
        Link("backend", "ollama", [Msg("1.4", "oracion := generate(prompt)", "ab")]),
    ]
    return Diagram(
        "08_colaboracion_dc02",
        "DC-02 — cerrarOracionYTraducir(secuencia) — realiza CU-01 / CU-02",
        objects,
        links,
        title_w=610,
    )


# ---------------------------------------------------------------------------
# DC-03 — sintetizarVoz(oracion) — realiza CU-03
# grid: backend straight E to cache, straight S to piper; builder/audio
# form a separate straight-E pair on their own row, well clear of piper.
# ---------------------------------------------------------------------------
def dc03() -> Diagram:
    objects = [
        Obj("backend", "process_sentence : app.py", 0, 170, 200, 56),
        Obj("cache", "_audio_cache", 245, 170, 190, 56),
        Obj("piper", "piper_voice : PiperVoice", 0, 400, 200, 46),
        Obj("builder", "useSentenceBuilder", 245, 400, 180, 46),
        Obj("audio", "Audio (reproducción en navegador)", 470, 400, 220, 46),
    ]
    links = [
        Link(
            "backend",
            "cache",
            [
                Msg("1", "audioBase64 := _cache_get(oracion)", "ab"),
                Msg("2.1", "_cache_put(oracion, audioBase64)", "ab"),
            ],
        ),
        Link("backend", "piper", [Msg("2", "wav := synthesize_wav(oracion)", "ab")]),
        Link("builder", "audio", [Msg("3", "play(audio) tras DISPLAY_WINDOW_MS", "ab")]),
    ]
    return Diagram(
        "08_colaboracion_dc03",
        "DC-03 — sintetizarVoz(oracion) — realiza CU-03",
        objects,
        links,
        title_w=690,
    )


# ---------------------------------------------------------------------------
# DC-04 — enviarRespuesta(mensaje) — realiza CU-04
# 2-row snake (~620 px wide): controls->recPage->chatRec straight H on row 1;
# chatRec->bc drops via a bend so its (long, two-line) message lands on a
# horizontal sub-segment clear of both rows; bc->chatPac->bubble continue
# straight H on row 2, right to left.
# ---------------------------------------------------------------------------
def dc04() -> Diagram:
    objects = [
        Obj("controls", "ReceptionControls", 0, 200, 170, 56),
        Obj("recPage", "RecepcionPage", 230, 200, 150, 56),
        Obj("chatRec", "useChatChannel (Recepción)", 440, 200, 180, 56),
        Obj("bc", "BroadcastChannel (canal nexora-chat)", 445, 420, 170, 64),
        Obj("chatPac", "useChatChannel (Paciente)", 225, 420, 160, 64),
        Obj("bubble", "ChatBubble (Paciente)", 15, 420, 150, 64),
    ]
    chatRec = next(o for o in objects if o.id == "chatRec")
    bc = next(o for o in objects if o.id == "bc")
    a_pt = (chatRec.x + chatRec.w * 0.5, chatRec.y + chatRec.h)
    b_frac = 0.85
    b_pt = (bc.x + bc.w * b_frac, bc.y)
    links = [
        Link("controls", "recPage", [Msg("1", "onSend(texto)", "ab")]),
        Link("recPage", "chatRec", [Msg("2", "sendMessage(mensaje)", "ab")]),
        Link(
            "chatRec",
            "bc",
            [Msg("2.1", "postMessage(mensaje)", "ab", seg=0)],
            waypoints=[(a_pt[0], 340), (b_pt[0], 340)],
            a_exit=("bottom", 0.5),
            b_entry=("top", b_frac),
        ),
        Link("bc", "chatPac", [Msg("2.2", "onmessage(evento)", "ab")]),
        Link("chatPac", "bubble", [Msg("2.3", "setChatHistory(mensaje)", "ab")]),
    ]
    return Diagram(
        "08_colaboracion_dc04",
        "DC-04 — enviarRespuesta(mensaje) — realiza CU-04 (sincronización por BroadcastChannel)",
        objects,
        links,
        title_w=600,
    )


# ---------------------------------------------------------------------------
# DC-05 — capturarMuestra(frames, etiqueta) — realiza CU-06
# grid: capture straight E to handler (self-loop on handler's free top
# side); capture straight S to backend; backend straight E to validation,
# straight S to fs (no diagonal — fs sits directly below backend).
# ---------------------------------------------------------------------------
def dc05() -> Diagram:
    objects = [
        Obj("capture", "CaptureMode", 60, 80, 190, 46),
        Obj("handler", "captureHandlerRef (frame handler)", 380, 80, 250, 46),
        Obj("backend", "capture : app.py", 60, 380, 190, 46),
        Obj("validation", "capture_validation", 380, 380, 230, 46),
        Obj("fs", "dataset/custom/<etiqueta>/*.npy", 20, 650, 280, 46),
    ]
    links = [
        Link("capture", "handler", [Msg("1", "recordOneSample()", "ab")]),
        Link("handler", "handler", [Msg("1.1", "push(frame) hasta 45 frames", "ab")], self_loop=True, self_side="bottom"),
        Link("capture", "backend", [Msg("2", "POST /capture({label, frames})", "ab")]),
        Link(
            "backend",
            "validation",
            [
                Msg("2.1", "ok := validate_capture_label(label)", "ab"),
                Msg("2.2", "blendshapes := validate_capture_blendshapes(T, blendshapes)", "ab"),
            ],
        ),
        Link("backend", "fs", [Msg("2.3", "np.save(frames)", "ab")]),
    ]
    return Diagram(
        "08_colaboracion_dc05",
        "DC-05 — capturarMuestra(frames, etiqueta) — realiza CU-06",
        objects,
        links,
        title_w=900,
    )


# ---------------------------------------------------------------------------
# DC-06 — otorgarConsentimiento(paciente) — realiza CU-09 (RF-03)
# 2-row layout: pacientePage -> sendAudit -> backend straight H on row 1;
# backend -> fileAudit and pacientePage -> useMediaPipe each drop straight
# down on row 2 (object x-centers match, so both links stay vertical with
# no waypoints needed).
# ---------------------------------------------------------------------------
def dc06() -> Diagram:
    objects = [
        Obj("pacientePage", "PacientePage (diálogo de consentimiento)", 0, 200, 230, 56),
        Obj("sendAudit", "sendAudit() : audit.ts", 300, 200, 180, 56),
        Obj("backend", "audit_event : app.py", 550, 200, 170, 56),
        Obj("useMediaPipe", ":useMediaPipe", 30, 420, 170, 56),
        Obj("fileAudit", "logs/audit.jsonl", 540, 420, 190, 56),
    ]
    links = [
        Link("pacientePage", "sendAudit", [Msg("1", "sendAudit({type:'consent', consent})", "ab")]),
        Link("sendAudit", "backend", [Msg("1.1", "POST /audit(payload)", "ab")]),
        Link(
            "backend",
            "backend",
            [Msg("1.2", "_log_audit('consent', consent=...)", "ab")],
            self_loop=True,
            self_side="right",
        ),
        Link("backend", "fileAudit", [Msg("1.3", "_append_jsonl(record)", "ab")]),
        Link("pacientePage", "useMediaPipe", [Msg("2", "enabled=true", "ab")]),
        Link(
            "useMediaPipe",
            "useMediaPipe",
            [Msg("2.1", "getUserMedia()", "ab")],
            self_loop=True,
            self_side="bottom",
        ),
    ]
    return Diagram(
        "08_colaboracion_dc06",
        "DC-06 — otorgarConsentimiento(paciente) — realiza CU-09",
        objects,
        links,
        title_w=600,
    )


# ---------------------------------------------------------------------------
# DC-07 — registrarEventoAuditoria(operacion) — realiza CU-11 (RF-04)
# compact straight horizontal chain: any handler -> _log_audit -> _append_jsonl
# -> logs/audit.jsonl. _log_audit and _append_jsonl are both plain functions
# in app.py (no audit_log module); _append_jsonl writes under a
# threading.Lock shared by /report and /audit (see nota).
# ---------------------------------------------------------------------------
def dc07() -> Diagram:
    objects = [
        Obj("handler", "handler (predict / websocket_predict /\nprocess_sentence / report / audit_event)", 0, 200, 300, 64),
        Obj("logAudit", "_log_audit() : app.py", 340, 200, 170, 64),
        Obj("appendJsonl", "_append_jsonl() : app.py", 550, 200, 180, 64),
        Obj("fileAudit", "logs/audit.jsonl", 770, 200, 170, 64),
    ]
    links = [
        Link("handler", "logAudit", [Msg("1", "_log_audit(tipo, **campos)", "ab")]),
        Link("logAudit", "appendJsonl", [Msg("1.1", "_append_jsonl(AUDIT_LOG_PATH, record)", "ab")]),
        Link("appendJsonl", "fileAudit", [Msg("1.2", "write(json.dumps(record))", "ab")]),
    ]
    notes = [
        Note(
            "appendJsonl",
            520,
            60,
            "Escritura protegida por threading.Lock,\ncompartido con /report; en /ws/predict\nse despacha con asyncio.to_thread\npara no bloquear el loop de eventos.",
            230,
            76,
        )
    ]
    return Diagram(
        "08_colaboracion_dc07",
        "DC-07 — registrarEventoAuditoria(operacion) — realiza CU-11",
        objects,
        links,
        notes,
        title_w=650,
    )


# ---------------------------------------------------------------------------
# DC-08 — reportarTraduccion(mensaje) — realiza CU-10 (RF-06)
# 2-row layout: bubble -> backend -> validation straight H on row 1;
# backend -> appendJsonl (same x-center, straight down) -> fileReports on
# row 2; backend's self-loop covers the extra audit event it also emits
# (_log_audit('report', ...), full chain in DC-07).
# ---------------------------------------------------------------------------
def dc08() -> Diagram:
    objects = [
        Obj("bubble", "ChatBubble", 0, 200, 170, 64),
        Obj("backend", "report_translation : app.py", 260, 200, 210, 64),
        Obj("validation", "validate_report_payload() :\ncapture_validation.py", 570, 200, 240, 64),
        Obj("appendJsonl", "_append_jsonl() : app.py", 260, 420, 210, 64),
        Obj("fileReports", "logs/reports.jsonl", 570, 420, 200, 64),
    ]
    links = [
        Link("bubble", "backend", [Msg("1", "POST /report({text, station, words})", "ab")]),
        Link("backend", "validation", [Msg("1.1", "validate_report_payload(text, station, words)", "ab")]),
        Link("backend", "appendJsonl", [Msg("1.2", "_append_jsonl(REPORTS_LOG_PATH, record)", "ab")]),
        Link("appendJsonl", "fileReports", [Msg("1.3", "write(json.dumps(record))", "ab")]),
        Link(
            "backend",
            "backend",
            [Msg("1.4", "audita('report')", "ab")],
            self_loop=True,
            self_side="bottom",
            self_frac=(0.05, 0.30),
        ),
    ]
    return Diagram(
        "08_colaboracion_dc08",
        "DC-08 — reportarTraduccion(mensaje) — realiza CU-10",
        objects,
        links,
        title_w=700,
    )


# ---------------------------------------------------------------------------
# DC-09 — limpiarConversacion() — realiza CU-12 (RNF-03)
# 2-row layout, misma familia que DC-04/DC-06: fila 1 controls->chatRec->
# sendAudit->backend en cadena horizontal recta; fila 2 bc/fileAudit debajo
# de chatRec/backend (mismo centro x, enlace vertical directo, sin
# quiebres); chatPac a la izquierda de bc en la fila 2 (horizontal recto).
# ---------------------------------------------------------------------------
def dc09() -> Diagram:
    objects = [
        Obj("controls", "RecepcionPage", 0, 60, 230, 56),
        Obj("chatRec", "useChatChannel (Recepción)", 0, 230, 230, 56),
        Obj("bc", "BroadcastChannel", 0, 400, 230, 56),
        Obj("chatPac", "useChatChannel (Paciente)", 0, 570, 230, 56),
        Obj("sendAudit", "sendAudit() : audit.ts", 360, 230, 200, 56),
        Obj("backend", "audit_event : app.py", 360, 400, 200, 56),
        Obj("fileAudit", "logs/audit.jsonl", 360, 570, 200, 56),
    ]
    links = [
        Link("controls", "chatRec", [Msg("1", "clearHistory()", "ab")]),
        Link("chatRec", "bc", [Msg("1.1", "postMessage({type:'CLEAR'})", "ab")]),
        Link("bc", "chatPac", [Msg("1.1.1", "onmessage(CLEAR)", "ab")]),
        Link("chatRec", "sendAudit", [Msg("1.2", "sendAudit('fin_atencion')", "ab")]),
        Link("sendAudit", "backend", [Msg("1.2.1", "POST /audit(payload)", "ab")]),
        Link(
            "backend",
            "backend",
            [Msg("1.2.2", "_log_audit('fin_atencion')", "ab")],
            self_loop=True,
            self_side="right",
        ),
        Link("backend", "fileAudit", [Msg("1.2.3", "_append_jsonl(record)", "ab")]),
    ]
    return Diagram(
        "08_colaboracion_dc09",
        "DC-09 — limpiarConversacion() — realiza CU-12",
        objects,
        links,
        title_w=560,
    )


def main():
    for build in (dc01, dc02, dc03, dc04, dc05, dc06, dc07, dc08, dc09):
        d = build()
        xml = render(d)
        out_path = os.path.join(OUT_DIR, f"{d.name}.drawio")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
