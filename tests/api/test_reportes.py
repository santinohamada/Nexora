"""CU-10 backend: POST /report y GET /reports/summary."""
import re

from harness import tc, http, rows, short

UTC_ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}\+00:00$")


def rep(base, text="Me duele la cabeza.", station="paciente", **kw):
    return http(base, "POST", "/report", {"text": text, "station": station, **kw})


@tc("TC-LSA-010-04")
def registro_y_persistencia(base):
    c = base.c
    body = dict(text="Me duele la cabeza.", station="paciente", words=["yo", "cabeza", "dolor"], message_id=1700000000001)
    st, r = http(base, "POST", "/report", body)
    c.ok(st == 200 and r == {"status": "ok", "report_id": 1, "message_id": 1}, '200 {"status":"ok","report_id":1,"message_id":1}', f"{st} {short(r)}")
    c.note(f"1ra -> {st} {short(r)}")
    st, r2 = http(base, "POST", "/report", body)
    c.ok(st == 200 and r2.get("message_id") == 1 and r2.get("report_id") == 2, "200 con el mismo message_id (1) y report_id nuevo (2)", f"{st} {short(r2)}")
    c.note(f"repeticion -> {st} {short(r2)}")
    ids = []
    for _ in range(2):
        st, r3 = rep(base, station="recepcion")
        ids.append(r3.get("message_id"))
        c.eq(st, 200, "HTTP de reporte sin message_id")
    c.ok(len(set(ids)) == 2 and 1 not in ids, "dos peticiones sin message_id crean dos mensajes distintos", ids)
    c.note(f"sin message_id (recepcion) x2 -> message_id {ids}")
    words = rows(base.db, "SELECT message_id, position, word FROM recognized_word ORDER BY message_id, position")
    c.ok([w["message_id"] for w in words] == [1, 1, 1], "recognized_word no se duplica en el segundo reporte (3 filas del mensaje 1)", words)
    tr = rows(base.db, "SELECT id, message_id, station, reported_at FROM translation_report ORDER BY id")
    c.ok(len(tr) == 4 and all(UTC_ISO.match(t["reported_at"]) for t in tr), "una fila por reporte con reported_at UTC ISO 8601", tr)
    c.eq([t["station"] for t in tr], ["paciente", "paciente", "recepcion", "recepcion"], "station por reporte")
    au = rows(base.db, "SELECT type FROM audit_event WHERE type='report'")
    c.eq(len(au), 4, 'filas audit_event type="report"')
    c.note(f"recognized_word={[w['word'] for w in words]}; translation_report={[(t['id'], t['message_id'], t['station']) for t in tr]} "
           f"reported_at ej.={tr[0]['reported_at']}; audit_event report={len(au)}")


@tc("TC-LSA-010-05")
def limites_text_station(base):
    c = base.c
    for text, st_ in [("a", "paciente"), ("a", "recepcion"), ("x" * 500, "paciente"), ("x" * 500, "recepcion")]:
        st, r = rep(base, text, st_)
        c.eq(st, 200, f"text de {len(text)} car. / {st_}")
        c.note(f"text {len(text)} car., {st_} -> {st}")
    exp = [("501 car.", {"text": "x" * 501, "station": "paciente"}, 400, {"detail": "Text too long"}),
           ("text vacio", {"text": "", "station": "paciente"}, 400, {"detail": "Empty text"}),
           ("text solo espacios", {"text": "   ", "station": "paciente"}, 400, {"detail": "Empty text"}),
           ("text numerico 5", {"text": 5, "station": "paciente"}, 422, None),
           ("sin station", {"text": "hola"}, 422, None),
           ("station admin", {"text": "hola", "station": "admin"}, 400, {"detail": "Invalid station"}),
           ("station Paciente", {"text": "hola", "station": "Paciente"}, 400, {"detail": "Invalid station"}),
           ("station vacia", {"text": "hola", "station": ""}, 400, {"detail": "Invalid station"})]
    for name, body, want_st, want_body in exp:
        st, r = http(base, "POST", "/report", body)
        c.ok(st == want_st and (want_body is None or r == want_body), f"{name} -> {want_st} {want_body or ''}", f"{st} {short(r, 100)}")
        c.note(f"{name} -> {st} {short(r, 80)}")
    sql = "x'); DROP TABLE reported_message;--"
    emo = "Me duele el corazón 😀 ñandú"
    for t in (sql, emo):
        st, r = rep(base, t)
        c.eq(st, 200, f"HTTP con texto {t[:12]!r}")
    texts = [x["text"] for x in rows(base.db, "SELECT text FROM reported_message")]
    tables = {x["name"] for x in rows(base.db, "SELECT name FROM sqlite_master WHERE type='table'")}
    c.ok(sql in texts and emo in texts, "el texto se guarda literalmente", texts[-2:])
    c.ok({"reported_message", "recognized_word", "translation_report", "audit_event"} <= tables, "las tablas siguen intactas", sorted(tables))
    c.note(f"textos guardados literalmente: {texts[-2:]}; tablas: {sorted(tables)}")


@tc("TC-LSA-010-06")
def limites_words_message_id(base):
    c = base.c
    w = lambda ws: {"text": "hola", "station": "paciente", "words": ws}
    m = lambda mid: {"text": "hola", "station": "paciente", "message_id": mid}
    cases = [
        ("20 words", w(["a"] * 20), 200, None), ("[] words", w([]), 200, None),
        ("21 words", w(["a"] * 21), 400, {"detail": "Too many words"}),
        ("palabra de 32 car.", w(["a" * 32]), 200, None),
        ("palabra de 33 car.", w(["a" * 33]), 400, {"detail": "Invalid word"}),
        ("palabra vacia", w([""]), 400, {"detail": "Invalid word"}),
        ("message_id 0", m(0), 200, None), ("message_id 2^53-1", m(9007199254740991), 200, None),
        ("message_id -1", m(-1), 400, {"detail": "Invalid message_id"}),
        ("message_id 2^53", m(9007199254740992), 400, {"detail": "Invalid message_id"}),
        ("message_id 1.5", m(1.5), 422, None), ("message_id 'abc'", m("abc"), 422, None),
        ("message_id true", m(True), 400, {"detail": "Invalid message_id"}),
        ("message_id '12'", m("12"), 422, None),
    ]
    for name, body, want_st, want_body in cases:
        st, r = http(base, "POST", "/report", body)
        c.ok(st == want_st and (want_body is None or r == want_body), f"{name} -> {want_st} {want_body or ''}", f"{st} {short(r, 100)}")
        c.note(f"{name} -> {st}")


@tc("TC-LSA-010-07")
def resumen(base):
    c = base.c
    for i in range(104):
        rep(base, f"Mensaje de prueba {i:03d}")
    for _ in range(4):
        rep(base, "Me duele la cabeza.", words=["yo", "cabeza", "dolor"], message_id=1700000000001)
    g = lambda q: http(base, "GET", "/reports/summary" + q)
    st, r = g("")
    top = r.get("top_messages", [])
    c.ok(st == 200 and {"total_reports", "top_messages", "top_words"} <= set(r), "200 con total_reports, top_messages y top_words", f"{st} {list(r)}")
    c.ok(len(top) == 10, "top_messages hasta 10", len(top))
    c.ok(top and top[0]["text"] == "Me duele la cabeza." and top[0]["reports"] == 4 and top[0].get("last_reported_at"),
         'primer mensaje "Me duele la cabeza." con reports=4 y last_reported_at', short(top[:1]))
    c.ok({"word": "cabeza", "reports": 4} in r.get("top_words", []), 'top_words incluye {"word":"cabeza","reports":4}', r.get("top_words"))
    c.note(f"sin parametros: total_reports={r.get('total_reports')} top_messages={len(top)} primero={short(top[:1])} top_words={r.get('top_words')}")
    for q, want in [("?limit=1", 1), ("?limit=5", 5), ("?limit=0", 1), ("?limit=-3", 1),
                    ("?limit=100", 100), ("?limit=101", 100), ("?limit=1000", 100)]:
        st, r = g(q)
        n = len(r.get("top_messages", [])) if isinstance(r, dict) else None
        c.ok(st == 200 and n == want, f"{q} -> {want} elementos", f"{st} {n}")
        c.note(f"{q} -> {st}, {n} elementos")
    st, r = g("?limit=abc")
    c.eq(st, 422, "HTTP de limit=abc")
    c.note(f"limit=abc -> {st}")
