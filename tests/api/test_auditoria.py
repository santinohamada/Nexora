"""CU-11 backend: POST /audit, GET /metrics y eventos propios del backend."""
import sqlite3
from datetime import datetime, timedelta, timezone
import time

from harness import tc, http, rows, wait_for, ws_open, ws_window, sample, db_bytes, short
from test_reportes import UTC_ISO

COLS = ["id", "type", "occurred_at", "station", "consent", "lstm_ms", "confidence", "translation_ms", "tts_ms",
        "total_ms", "e2e_ms", "source", "word_count"]


def audit(base, **body):
    return http(base, "POST", "/audit", body)


def n_rows(base):
    return rows(base.db, "SELECT COUNT(*) AS n FROM audit_event")[0]["n"]


@tc("TC-LSA-011-01")
def consentimiento(base):
    c = base.c
    for consent in ("accepted", "declined"):
        st, r = audit(base, type="consent", station="paciente", consent=consent)
        c.ok(st == 200 and r == {"status": "ok"}, '200 {"status":"ok"}', f"{st} {short(r)}")
        c.note(f"consent={consent} -> {st} {short(r)}")
    ev = rows(base.db, "SELECT * FROM audit_event ORDER BY id")
    nulls = ["lstm_ms", "confidence", "translation_ms", "tts_ms", "total_ms", "e2e_ms", "source", "word_count"]
    c.ok(len(ev) == 2 and all(e["type"] == "consent" and e["station"] == "paciente" for e in ev), "2 filas type=consent station=paciente", ev)
    c.eq([e["consent"] for e in ev], ["accepted", "declined"], "consent por fila")
    c.ok(all(UTC_ISO.match(e["occurred_at"]) for e in ev), "occurred_at en UTC ISO 8601", [e["occurred_at"] for e in ev])
    c.ok(all(e[k] is None for e in ev for k in nulls), "resto de campos nulos", ev)
    st, m = http(base, "GET", "/metrics")
    c.ok(m["counts"].get("consent") == 2 and m["consent"] == {"accepted": 1, "declined": 1}, 'counts.consent = 2 y consent = {"accepted":1,"declined":1}', short(m))
    c.note(f"filas={len(ev)} ej. occurred_at={ev[0]['occurred_at']}; /metrics counts={m['counts']} consent={m['consent']}")


@tc("TC-LSA-011-02")
def validacion_audit(base):
    c = base.c
    n0 = n_rows(base)
    def inv(body, want, name):
        st, r = http(base, "POST", "/audit", body)
        c.ok(st == 400 and r == {"detail": want}, f"{name} -> 400 {want}", f"{st} {short(r, 80)}")
        c.note(f"{name} -> {st} {short(r, 60)}")
    for t in ("prediction", "fin_atencion", "x"):
        inv({"type": t, "station": "paciente"}, "Invalid audit type", f"type {t!r}")
    inv({"type": "consent", "station": "x", "consent": "accepted"}, "Invalid station", "station 'x'")
    st, r = http(base, "POST", "/audit", {"type": "consent", "consent": "accepted"})
    c.eq(st, 422, "HTTP sin station")
    c.note(f"sin station -> {st}")
    inv({"type": "consent", "station": "paciente"}, "Invalid consent value", "consent ausente")
    inv({"type": "consent", "station": "paciente", "consent": "maybe"}, "Invalid consent value", "consent 'maybe'")
    ok_rows = 0
    for v in (0, 60000):
        st, r = audit(base, type="translation_displayed", station="paciente", e2e_ms=v)
        c.eq(st, 200, f"e2e_ms={v} (HTTP)")
        ok_rows += st == 200
        c.note(f"e2e_ms={v} -> {st}")
    for v in (60000.01, -1):
        inv({"type": "translation_displayed", "station": "paciente", "e2e_ms": v}, "Invalid e2e_ms", f"e2e_ms={v}")
    inv({"type": "translation_displayed", "station": "paciente", "e2e_ms": None}, "Invalid e2e_ms", "e2e_ms null")
    inv({"type": "translation_displayed", "station": "paciente"}, "Invalid e2e_ms", "e2e_ms omitido")
    c.eq(n_rows(base) - n0, ok_rows, "filas insertadas = peticiones con 200")
    n1 = n_rows(base)
    extra = [http(base, "POST", "/audit", {"type": "translation_displayed", "station": "paciente", "e2e_ms": v})[0] for v in ("5", True)]
    c.note(f"filas antes={n0}, despues={n1}; D-17 (informativo): e2e_ms '5' y true -> HTTP {extra}")


@tc("TC-LSA-011-03")
def eventos_backend(base):
    c = base.c
    with ws_open(base, "?v=1") as ws:
        for i in range(3):
            ws_window(ws, sample("dolor", i))
    wait_for(lambda: n_rows(base) >= 3, 5)
    for w in ("yo cabeza dolor", "dolor yo cabeza"):
        http(base, "POST", "/process_sentence", {"words": w})
    http(base, "POST", "/report", {"text": "Me duele la cabeza.", "station": "paciente"})
    pred = rows(base.db, "SELECT * FROM audit_event WHERE type='prediction'")
    sent = rows(base.db, "SELECT * FROM audit_event WHERE type='sentence'")
    rep = rows(base.db, "SELECT * FROM audit_event WHERE type='report'")
    c.ok(len(pred) == 3 and all(p["lstm_ms"] and p["lstm_ms"] > 0 and 0 <= p["confidence"] <= 100 and p["station"] is None for p in pred),
         "3 filas prediction con lstm_ms > 0, confidence 0-100 y sin station", pred)
    c.ok(len(sent) == 2 and all(s["translation_ms"] >= 0 and s["tts_ms"] >= 0 and s["total_ms"] >= 0 and s["source"] == "template"
                                and s["word_count"] == 3 for s in sent), "2 filas sentence con tiempos >= 0, source=template, word_count=3", sent)
    c.ok(len(rep) == 1 and rep[0]["station"] == "paciente", "1 fila report con station", rep)
    allr = rows(base.db, "SELECT * FROM audit_event")
    strings = {k: v for r in allr for k, v in r.items() if isinstance(v, str) and k not in ("type", "occurred_at", "station", "source", "consent")}
    c.ok(not strings and list(allr[0]) == COLS, "ningun registro contiene texto de conversacion, frames ni audio", strings or list(allr[0]))
    c.note(f"prediction: lstm_ms={[p['lstm_ms'] for p in pred]} conf={[p['confidence'] for p in pred]}; "
           f"sentence: {[(s['translation_ms'], s['tts_ms'], s['total_ms'], s['source'], s['word_count']) for s in sent]}; report: {len(rep)}")


@tc("TC-LSA-011-05")
def metricas(base):
    c = base.c
    empty = {"counts": {}, "consent": {"accepted": 0, "declined": 0}, "reports": 0, "translation_source": {}, "latency_ms": {}}
    st, m = http(base, "GET", "/metrics")
    c.ok(st == 200 and m == empty, f"200 {empty}", f"{st} {short(m)}")
    for v in (100, 200, 300, 400):
        audit(base, type="translation_displayed", station="paciente", e2e_ms=v)
    st, m = http(base, "GET", "/metrics")
    c.eq(m["latency_ms"].get("e2e_ms"), {"p50": 200.0, "p95": 400.0, "max": 400.0, "count": 4}, "latency_ms.e2e_ms")
    c.note(f"base vacia -> {short(empty)}; tras 4 eventos latency_ms.e2e_ms={m['latency_ms'].get('e2e_ms')}")
    st, m = http(base, "GET", "/metrics?since=2099-01-01T00:00:00")
    c.ok(st == 200 and m["counts"] == {}, "since futuro -> counts vacio", f"{st} {short(m['counts'] if isinstance(m, dict) else m)}")
    st, m = http(base, "GET", "/metrics?since=ayer")
    c.ok(st == 400 and m == {"detail": "Invalid since timestamp"}, "since=ayer -> 400 Invalid since timestamp", f"{st} {short(m)}")
    # Real filter check: the 4 events above exist; a `since` after them (ISO with Z, as Date.toISOString) must exclude them
    # and a `since` before them must include them.
    now = datetime.now(timezone.utc)
    after_z = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    before_z = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    st_a, m_a = http(base, "GET", "/metrics?since=" + after_z)
    n_a = m_a["counts"].get("translation_displayed", 0) if st_a == 200 and isinstance(m_a, dict) else None
    c.ok(st_a == 200 and n_a == 0, f"since={after_z} (posterior a los eventos) -> 200 y counts sin translation_displayed", f"{st_a} {short(m_a)}")
    st_b, m_b = http(base, "GET", "/metrics?since=" + before_z)
    n_b = m_b["counts"].get("translation_displayed", 0) if st_b == 200 and isinstance(m_b, dict) else None
    c.ok(st_b == 200 and n_b == 4, f"since={before_z} (anterior a los eventos) -> 200 y translation_displayed = 4", f"{st_b} {short(m_b)}")
    c.note(f"since posterior (Z) -> {st_a} translation_displayed={n_a}; since anterior (Z) -> {st_b} translation_displayed={n_b}")


@tc("TC-LSA-011-06")
def anonimato(base):
    c = base.c
    cols = [r["name"] for r in rows(base.db, "PRAGMA table_info(audit_event)")]
    types = {r["name"]: r["type"] for r in rows(base.db, "PRAGMA table_info(audit_event)")}
    c.eq(cols, COLS, "columnas de audit_event")
    c.ok("BLOB" not in types.values(), "sin columnas binarias", types)
    st, r = audit(base, type="consent", station="recepcion", consent="accepted", name="Juan Perez", text="hola", ip="10.0.0.5")
    c.ok(st == 200, "POST /audit con campos extra -> 200", f"{st} {short(r)}")
    ev = rows(base.db, "SELECT * FROM audit_event")[-1]
    c.ok(set(ev) == set(COLS) and "Juan Perez" not in str(ev), "el evento se guarda sin los campos extra", ev)
    with ws_open(base, "?v=1") as ws:
        ws_window(ws, sample("dolor"))
    http(base, "POST", "/process_sentence", {"words": "dolor"})
    http(base, "POST", "/report", {"text": "Me duele la cabeza.", "station": "paciente", "words": ["yo", "cabeza", "dolor"]})
    time.sleep(0.5)
    files = db_bytes(base.db)
    found = {n: [s for s in ("Juan Perez", "Tengo dolor.", "10.0.0.5") if s.encode() in b] for n, b in files.items()}
    c.ok(not any(found.values()), 'ni "Juan Perez" ni "Tengo dolor." aparecen en la base ni en -wal/-shm', found)
    c.note(f"columnas={cols}; evento con extras: {ev}; archivos revisados {sorted(files)} ({ {k: len(v) for k, v in files.items()} } bytes); coincidencias={found}")


@tc("TC-LSA-011-07")
def fallo_de_auditoria(base):
    c = base.c
    lock = sqlite3.connect(base.db, timeout=1, isolation_level=None)
    lock.execute("BEGIN EXCLUSIVE")
    try:
        t0 = time.time()
        st, r = http(base, "POST", "/process_sentence", {"words": "dolor"})
        el1 = time.time() - t0
        c.ok(st == 200 and r.get("natural_sentence") == "Tengo dolor.", "bloqueada: process_sentence -> 200 'Tengo dolor.'", f"{st} {short(r, 100)}")
        t0 = time.time()
        st2, r2 = audit(base, type="consent", station="paciente", consent="accepted")
        el2 = time.time() - t0
        c.eq(st2, 500, "bloqueada: HTTP de POST /audit")
        c.note(f"con la base bloqueada: process_sentence -> {st} en {el1:.1f} s; /audit -> {st2} {short(r2, 40)} en {el2:.1f} s")
    finally:
        lock.execute("ROLLBACK")
        lock.close()
    st, r = http(base, "POST", "/process_sentence", {"words": "dolor"})
    st2, r2 = audit(base, type="consent", station="paciente", consent="accepted")
    c.ok(st == 200 and st2 == 200, "liberada: ambas peticiones responden 200", f"{st}, {st2}")
    m = http(base, "GET", "/metrics")[1]["counts"]
    c.ok(m.get("sentence") == 1 and m.get("consent") == 1, "tras liberar se registran los eventos (1 sentence, 1 consent; los del bloqueo se perdieron)", m)
    c.note(f"tras liberar: {st}, {st2}; counts={m}")
