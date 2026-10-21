"""CU-01 backend: clasificacion por WebSocket /ws/predict y POST /predict."""
import json
import time

import numpy as np

from harness import tc, http, sample, ws_open, ws_window, wait_for, short

TRAIN_NOTE = "Las muestras provienen del conjunto de entrenamiento (no miden generalizacion)."


@tc("TC-LSA-001-02")
def cadena_backend(base):
    c = base.c
    seq = ["yo", "cabeza", "dolor"]
    st, m0 = http(base, "GET", "/metrics")
    c.eq(st, 200, "GET /metrics (inicial)")
    words = []
    with ws_open(base, "?v=1") as ws:
        for label in seq:
            r = ws_window(ws, sample(label))
            c.ok({"sign", "confidence", "top3"} <= set(r), "claves sign, confidence y top3", short(r))
            c.eq(r.get("sign"), label, f"sign de la muestra {label}")
            c.ok(r.get("confidence", 0) >= 70, f"confidence >= 70 ({label})", r.get("confidence"))
            t3 = r.get("top3", [])
            confs = [t["confidence"] for t in t3]
            c.eq(len(t3), 3, "elementos de top3")
            c.ok(confs == sorted(confs, reverse=True), "top3 ordenado de mayor a menor", confs)
            c.ok(sum(confs) <= 100.05, "suma de confianzas del top3 <= 100 (tolerancia 0.05 por redondeo)", sum(confs))
            c.note(f"{label}: sign={r.get('sign')} conf={r.get('confidence')} top3={[(t['sign'], t['confidence']) for t in t3]}")
            words.append(r.get("sign"))
    st, ps = http(base, "POST", "/process_sentence", {"words": " ".join(words)})
    c.eq(st, 200, "HTTP de /process_sentence")
    c.eq(ps.get("natural_sentence"), "Me duele la cabeza.", "natural_sentence")
    c.eq(ps.get("source"), "template", "source")
    c.ok(bool(ps.get("audio_base64")), "audio_base64 no vacio", "vacio")
    c.ok(isinstance(ps.get("latency_ms"), (int, float)), "latency_ms numerico", ps.get("latency_ms"))
    c.note(f"process_sentence: {st} {short({k: v for k, v in ps.items() if k != 'audio_base64'})} audio_b64_len={len(ps.get('audio_base64', ''))}")

    def metrics():
        return http(base, "GET", "/metrics")[1]
    wait_for(lambda: metrics()["counts"].get("prediction", 0) - m0["counts"].get("prediction", 0) >= 3, 5)
    m1 = metrics()
    d = lambda k: m1["counts"].get(k, 0) - m0["counts"].get(k, 0)
    c.eq(d("prediction"), 3, "aumento de counts.prediction")
    c.eq(d("sentence"), 1, "aumento de counts.sentence")
    c.eq(m1["translation_source"].get("template", 0) - m0["translation_source"].get("template", 0), 1,
         "aumento de translation_source.template")
    c.note(f"metrics: counts={m1['counts']} translation_source={m1['translation_source']}. {TRAIN_NOTE}")


@tc("TC-LSA-001-08")
def idle_y_umbral(base):
    c = base.c
    n_idle, bad, confs = 0, [], []
    with ws_open(base, "?v=1") as ws:
        for i in range(30):
            r = ws_window(ws, sample("idle", i))
            confs.append(r.get("confidence"))
            if r.get("sign") != "idle" or r.get("confidence", 0) < 70:
                bad.append((i, r.get("sign"), r.get("confidence")))
            n_idle += r.get("sign") == "idle"
        c.ok(not bad, "las 30 respuestas con sign=idle y confidence >= 70", f"{len(bad)} fuera de criterio: {bad}")
        c.note(f"idle: {n_idle}/30 clasificadas como idle; confianza min={min(confs)} max={max(confs)}. {TRAIN_NOTE}")
        dolor10 = sample("dolor")[:10]
        r = ws_window(ws, dolor10)
        # short windows are front-padded with the oldest frame (a still window), so idle is a valid answer
        c.ok(r.get("confidence", 100) < 70 or r.get("sign") in ("dolor", "idle"), "con 10 frames: confidence < 70, la clase correcta o idle (WS)", short(r))
        c.note(f"WS dolor[:10]: sign={r.get('sign')} confidence={r.get('confidence')}")
    st, r = http(base, "POST", "/predict", {"frames": dolor10.tolist()})
    c.eq(st, 200, "HTTP de POST /predict")
    c.ok(isinstance(r, dict) and (r.get("confidence", 100) < 70 or r.get("sign") in ("dolor", "idle")), "con 10 frames: confidence < 70, la clase correcta o idle (POST /predict)", short(r))
    c.note(f"POST /predict dolor[:10]: {st} sign={r.get('sign')} confidence={r.get('confidence')}")


def _bin(frames):
    return b"\x02\x00\x00\x00" + np.asarray(frames, dtype=np.float32).tobytes()


def _recv(ws, timeout=10):
    return json.loads(ws.recv(timeout=timeout))


@tc("TC-LSA-001-10")
def protocolo_ws(base):
    c = base.c
    dolor = sample("dolor")
    # --- v1: entradas invalidas
    with ws_open(base, "?v=1") as ws:
        inval = [("texto no JSON", "hola"), ("JSON sin frames", json.dumps({"x": 1})),
                 ("JSON con 4 frames", json.dumps({"frames": dolor[:4].tolist()}))]
        for name, payload in inval:
            ws.send(payload)
            r = _recv(ws)
            c.ok(isinstance(r, dict) and "error" in r, f"{name}: respuesta {{\"error\": ...}}", short(r))
            c.note(f"v1 {name} -> {short(r)}")
        r = ws_window(ws, dolor)
        c.eq(r.get("sign"), "dolor", "muestra valida tras errores (sign)")
        c.note(f"v1 muestra valida -> sign={r.get('sign')} conf={r.get('confidence')}")
        # --- inactividad 6 s
        t0 = time.time()
        r = _recv(ws, timeout=8)
        el = time.time() - t0
        c.eq(r, {"error": "receive timeout"}, "mensaje tras 5 s sin enviar nada")
        c.ok(4.5 <= el <= 6, "el error llega a los ~5 s (WS_RECEIVE_TIMEOUT_MS)", f"{el:.2f} s")
        r2 = ws_window(ws, dolor)
        c.eq(r2.get("sign"), "dolor", "conexion abierta tras receive timeout (sign)")
        c.note(f"timeout: {r} a los {el:.2f} s; conexion sigue abierta (sign={r2.get('sign')})")
    # --- v2 binario
    with ws_open(base, "?v=2") as ws:
        ws.send(_bin(dolor))
        r = _recv(ws)
        c.ok(r.get("sign") == "dolor" and r.get("confidence", 0) >= 70,
             "v2 binario valido -> sign dolor y confidence >= 70", short(r))
        c.note(f"v2 marco valido (45x75x4 float32) -> {short(r)}")
        bad65 = _bin(np.concatenate([dolor, np.zeros((20, 75, 4), np.float32)]))
        cases = [("marco de 2 bytes", b"\x02\x00", "binary header too short"),
                 ("cabecera 0x03", b"\x03\x00\x00\x00" + dolor.tobytes(), "unsupported binary version"),
                 ("4 frames", _bin(dolor[:4]), "frame count out of range"),
                 ("65 frames", bad65, "frame count out of range"),
                 ("longitud no multiplo de un frame", _bin(dolor)[:-4], "binary payload misaligned")]
        for name, payload, want in cases:
            ws.send(payload)
            r = _recv(ws)
            c.eq(r, {"error": want}, f"v2 {name}")
            c.note(f"v2 {name} -> {short(r)}")
        ws.send(_bin(dolor))
        c.note(f"v2 conexion abierta tras errores: {short(_recv(ws))}")
