"""Privacidad y seguridad (RNF-03, RNF-03.1, RNF-T-06) en el backend."""
import numpy as np

from harness import tc, http, rows, db_bytes, snapshot, ws_open, ws_window, sample, short, connect


@tc("TC-LSA-013-01")
def sin_conversacion(base):
    c = base.c
    sents = {}
    for w in ("dolor", "yo cabeza dolor", "respirar yo", "cabeza", "yo"):
        sents[w] = http(base, "POST", "/process_sentence", {"words": w})[1]["natural_sentence"]
    st, r = http(base, "POST", "/report", {"text": "Tengo dolor.", "station": "paciente"})
    c.eq(st, 200, "HTTP de /report")
    texts = [x["text"] for x in rows(base.db, "SELECT text FROM reported_message")]
    c.eq(texts, ["Tengo dolor."], "reported_message")
    files = db_bytes(base.db)
    others = [s for s in sents.values() if s != "Tengo dolor."]
    hits = {n: [s for s in others if s.encode() in b] for n, b in files.items()}
    c.ok(not any(hits.values()), "las otras cuatro oraciones no aparecen en la base ni en -wal/-shm", hits)
    types = {(t["name"], col["name"]): col["type"] for t in rows(base.db, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
             for col in rows(base.db, f"PRAGMA table_info({t['name']})")}
    c.ok(not any("BLOB" in str(t).upper() for t in types.values()), "sin columnas BLOB", {k: v for k, v in types.items() if "BLOB" in str(v).upper()})
    media = sorted(k for k in snapshot(base.tree) if k.lower().endswith((".png", ".jpg", ".webm", ".mp4", ".wav")))
    c.ok(not media, "sin archivos de imagen, video o audio en el proyecto", media)
    c.note(f"oraciones generadas={list(sents.values())}; reported_message={texts}; archivos de base revisados={sorted(files)}; "
           f"tipos de columna={sorted(set(types.values()))}")


@tc("TC-LSA-013-02")
def sin_imagenes(base):
    c = base.c
    before = snapshot(base.tree)
    labels = ["cabeza", "dolor", "idle", "respirar", "yo"]
    with ws_open(base, "?v=1") as ws:
        for i in range(50):
            r = ws_window(ws, sample(labels[i % 5], i // 5))
            assert "sign" in r, r
    for i in range(5):
        st, _ = http(base, "POST", "/predict", {"frames": sample(labels[i], 0).tolist()})
        assert st == 200, st
    after = snapshot(base.tree)
    changed = sorted(k for k in after if before.get(k) != after[k])
    c.ok(not changed, "no hay archivos nuevos ni modificados en el arbol del proyecto (excluida la base SQLite)", changed)
    media = [k for k in changed if k.lower().endswith((".png", ".jpg", ".webm", ".mp4", ".wav", ".npy"))]
    c.ok(not media, "no existen archivos .png/.jpg/.webm/.mp4/.wav/.npy nuevos", media)
    c.note(f"50 ventanas por /ws/predict + 5 por POST /predict; archivos del arbol {len(before)} antes / {len(after)} despues; nuevos o modificados: {changed}")


@tc("TC-LSA-013-04")
def cors(base):
    c = base.c
    good, evil = "http://localhost:3000", "http://evil.example.com"
    st, h, _ = http(base, "GET", "/", headers={"Origin": good}, full=True)
    acao = h.get("access-control-allow-origin")
    c.eq(acao, good, "Access-Control-Allow-Origin para http://localhost:3000")
    c.note(f"Origin {good} -> ACAO={acao!r}")
    st, h, _ = http(base, "GET", "/", headers={"Origin": evil}, full=True)
    acao = h.get("access-control-allow-origin")
    c.ok(acao is None, "sin Access-Control-Allow-Origin para el origen ajeno", f"ACAO={acao!r}")
    c.note(f"Origin {evil} -> {st} ACAO={acao!r}")
    import urllib.error, urllib.request
    from websockets.exceptions import ConnectionClosed, InvalidStatus
    req = urllib.request.Request(base + "/report", method="OPTIONS", headers={
        "Origin": evil, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    try:
        r = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as err:
        r = err
    acao = r.headers.get("access-control-allow-origin")
    c.ok(acao is None and r.status != 200, "el preflight no concede el origen ajeno", f"{r.status} ACAO={acao!r}")
    c.note(f"preflight OPTIONS /report con origen ajeno -> {r.status} ACAO={acao!r} allow-methods={r.headers.get('access-control-allow-methods')!r}")
    try:
        with connect(base.replace("http://", "ws://") + "/ws/predict", additional_headers={"Origin": evil}, open_timeout=10) as ws:
            reply = ws_window(ws, sample("dolor"))
            c.ok(False, "WebSocket con origen ajeno rechazado o cerrado", f"conexion aceptada y respondio {reply.get('sign')} ({reply.get('confidence')})")
            c.note(f"WebSocket con Origin ajeno: aceptado, prediccion={reply.get('sign')}")
    except (InvalidStatus, ConnectionClosed) as ex:
        c.note(f"WebSocket con Origin ajeno rechazado: {type(ex).__name__}")
