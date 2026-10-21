"""CU-02 (traduccion) y CU-03 (sintesis de voz) en el backend: POST /process_sentence."""
import base64
import io
import json
import re
import socket
import threading
import time
import wave

from harness import tc, http, server, free_port, ollama_warm, need_voices, Blocked, short, wait_for


def ps(base, words, timeout=60):
    t0 = time.time()
    st, r = http(base, "POST", "/process_sentence", {"words": words}, timeout=timeout)
    return st, r, (time.time() - t0) * 1000


def brief(r):
    return short({k: (f"<{len(v)} chars>" if k == "audio_base64" else v) for k, v in r.items()}) if isinstance(r, dict) else short(r)


@tc("TC-LSA-002-01")
def plantilla(base):
    c = base.c
    for words, want in [("yo cabeza dolor", "Me duele la cabeza."), ("dolor", "Tengo dolor."),
                        ("cabeza dolor respirar yo", "Me duele la cabeza, no puedo respirar bien.")]:
        st, r, ms = ps(base, words)
        c.eq(st, 200, f"HTTP de '{words}'")
        c.eq(r.get("original"), words, "original")
        c.eq(r.get("natural_sentence"), want, f"natural_sentence de '{words}'")
        c.eq(r.get("source"), "template", f"source de '{words}'")
        c.ok(bool(r.get("audio_base64")), "audio_base64 presente", "ausente")
        c.ok(isinstance(r.get("latency_ms"), (int, float)), "latency_ms numerico", r.get("latency_ms"))
        c.note(f"'{words}' -> {st} {brief(r)}")


@tc("TC-LSA-002-02")
def normalizacion(base):
    c = base.c
    n = lambda w: ps(base, w)
    for w, want in [("dolor yo cabeza", "Me duele la cabeza."), ("CABEZA Dolor YO", "Me duele la cabeza."),
                    ("yo yo cabeza dolor idle", "Me duele la cabeza."), ("idle dolor", "Tengo dolor."),
                    ("cabeza", "Tengo algo en la cabeza."), ("yo", "Necesito comunicar algo."),
                    ("respirar yo", "No puedo respirar bien."), ("dolor respirar yo", "Tengo dolor y no puedo respirar bien.")]:
        st, r, _ = n(w)
        c.ok(st == 200 and r.get("natural_sentence") == want and r.get("source") == "template",
             f"'{w}' -> 200, '{want}', template", f"{st} {brief(r)}")
        c.note(f"'{w}' -> {r.get('natural_sentence')} ({r.get('source')})")
    for w in ("", "   "):
        st, r, _ = n(w)
        c.ok(st == 400 and r == {"detail": "Empty words"}, f"words={w!r} -> 400 Empty words", f"{st} {short(r)}")
        c.note(f"words={w!r} -> {st} {short(r)}")
    st, r = http(base, "POST", "/process_sentence", {})
    c.eq(st, 422, "HTTP sin campo words")
    c.note(f"{{}} -> {st}")


@tc("TC-LSA-002-03")
def ollama_y_cache(base):
    c = base.c
    ollama_warm()
    absent = ["cabeza", "brazo", "fiebre", "tos", "mareo", "pierna", "espalda", "garganta", "estomago", "estómago",
              "cansancio", "nauseas", "náuseas", "vomito", "vómito", "corazon", "corazón", "panza"]
    st1, r1, ms1 = ps(base, "yo dolor pecho")
    c.eq(st1, 200, "HTTP de 'yo dolor pecho'")
    c.eq(r1.get("source"), "ollama", "source de la primera llamada")
    s1 = r1.get("natural_sentence", "")
    c.ok(bool(s1.strip()) and "pecho" in s1.lower(), "oracion no vacia que menciona 'pecho'", repr(s1))
    extra = [t for t in absent if t in s1.lower()]
    c.ok(not extra, "sin partes del cuerpo o sintomas ausentes de la secuencia", extra)
    st2, r2, ms2 = ps(base, "pecho dolor yo yo")
    c.eq(st2, 200, "HTTP de la segunda llamada")
    c.eq(r2.get("source"), "cache", "source de la segunda llamada")
    c.eq(r2.get("natural_sentence"), s1, "oracion identica a la primera")
    c.ok(r2.get("latency_ms", 999) <= 50, "latency_ms <= 50 en la llamada con cache", r2.get("latency_ms"))
    st, m = http(base, "GET", "/metrics")
    ts = m["translation_source"]
    c.ok(ts.get("ollama") == 1 and ts.get("cache") == 1, 'translation_source con "ollama": 1 y "cache": 1', ts)
    c.note(f"1ra: {brief(r1)} (cliente {ms1:.0f} ms); 2da: {brief(r2)} (cliente {ms2:.0f} ms); translation_source={ts}")


def _blackhole():
    """TCP listener that accepts and never answers (simulates an Ollama that does not respond)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(8)
    conns = []
    def loop():
        try:
            while True:
                conns.append(s.accept()[0])
        except OSError:
            pass
    threading.Thread(target=loop, daemon=True).start()
    return s, s.getsockname()[1]


@tc("TC-LSA-002-04", srv="tree")
def ollama_caido(base):
    c = base.c
    if not _ollama_reachable_check():
        raise Blocked("Ollama no responde en localhost:11434; no se puede comprobar el paso 3 (reinicio).")
    # app.py fija http://localhost:11434 sin variable de entorno: Ollama se simula caido con HTTP_PROXY
    # (requests lo respeta) apuntando a un puerto cerrado o a un socket que nunca responde.
    closed = free_port()
    with server(base.tree, base.db, env={"HTTP_PROXY": f"http://127.0.0.1:{closed}", "NO_PROXY": ""}) as b:
        st, r, ms = ps(b, "fiebre tos", timeout=40)
        log = b.log.read_text(encoding="utf-8", errors="replace")
        if "Ollama error" not in log:
            raise Blocked("No se logro simular Ollama caido (HTTP_PROXY no fue respetado por requests): " + short(r))
        c.eq(st, 200, "HTTP (Ollama caido, puerto cerrado)")
        c.eq(r.get("natural_sentence"), "fiebre tos", "natural_sentence = palabras originales")
        c.eq(r.get("source"), "ollama", "source")
        c.ok(bool(r.get("audio_base64")), "audio_base64 presente", "ausente")
        c.ok(ms <= 10000, "respuesta en <= 10 s", f"{ms:.0f} ms")
        c.note(f"Ollama caido (conexion rechazada): {st} {brief(r)} en {ms:.0f} ms")
        st2, r2, ms2 = ps(b, "fiebre tos", timeout=40)
        c.eq(r2.get("source"), "ollama", "segunda llamada: source sigue 'ollama' (la reserva no se cachea)")
        c.eq(r2.get("natural_sentence"), "fiebre tos", "segunda llamada: palabras originales")
        c.note(f"repeticion: {st2} source={r2.get('source')} en {ms2:.0f} ms")
    bh, port = _blackhole()
    try:
        with server(base.tree, base.db, env={"HTTP_PROXY": f"http://127.0.0.1:{port}", "NO_PROXY": ""}) as b:
            st, r, ms = ps(b, "fiebre tos", timeout=40)
            c.ok(st == 200 and r.get("natural_sentence") == "fiebre tos" and r.get("source") == "ollama" and ms <= 10000,
                 "Ollama sin responder: 200, palabras originales, source ollama, <= 10 s", f"{st} {brief(r)} en {ms:.0f} ms")
            c.note(f"Ollama sin responder (timeout 8 s): {st} {brief(r)} en {ms:.0f} ms")
    finally:
        bh.close()
    ollama_warm()
    with server(base.tree, base.db) as b:
        st, r, ms = ps(b, "fiebre tos", timeout=40)
        c.ok(st == 200 and r.get("source") == "ollama" and r.get("natural_sentence") not in ("fiebre tos", ""),
             "con Ollama activo la respuesta es una oracion generada por el modelo", f"{st} {brief(r)}")
        c.note(f"Ollama activo: {st} {brief(r)} en {ms:.0f} ms")


def _ollama_reachable_check():
    from harness import ollama_up
    return ollama_up()


LEAKS = ["NO agregues", "NO_CLARO", "Traducción:", "Palabras a traducir", "REGLA", "ejemplo", "Ejemplo", "(NO"]
CLIN = ["fiebre", "cansancio", "mareo", "tos", "brazo", "pecho", "cabeza", "pierna", "espalda", "garganta",
        "estómago", "náuseas", "vómito", "corazón", "medicamento", "pastilla"]


@tc("TC-LSA-002-05")
def fidelidad(base):
    c = base.c
    ollama_warm()
    for words in ("yo brazo dolor", "yo dolor pecho", "fiebre tos"):
        st, r, ms = ps(base, words)
        s = r.get("natural_sentence", "") if isinstance(r, dict) else ""
        c.eq(st, 200, f"HTTP de '{words}'")
        parts = [p for p in re.split(r"(?<=[.!?])\s+", s.strip()) if p]
        c.ok(len(parts) == 1, f"'{words}': una unica oracion", f"{len(parts)} fragmentos: {s!r}")
        leaks = [t for t in LEAKS if t in s]
        c.ok(not leaks, f"'{words}': sin fragmentos de instrucciones internas", f"{leaks} en {s!r}")
        seq = words.lower().split()
        added = [t for t in CLIN if re.search(r"\b" + re.escape(t) + r"\b", s, re.I) and t not in seq]
        c.ok(not added, f"'{words}': sin terminos clinicos ausentes de la secuencia (o texto original)",
             f"terminos agregados {added} en {s!r}")
        c.note(f"'{words}' -> {s!r} (source={r.get('source')}, {ms:.0f} ms)")


@tc("TC-LSA-002-06")
def no_claro(base):
    c = base.c
    ollama_warm()
    for words in ("idle idle", "idle"):
        st, r, ms = ps(base, words)
        s = r.get("natural_sentence")
        c.ok(st == 200 and s in ("NO_CLARO", ""), f"'{words}': natural_sentence = 'NO_CLARO' o vacio (se descarta)",
             f"{st} natural_sentence={s!r}")
        shown = bool(s) and s != "NO_CLARO"
        c.ok(not shown, f"'{words}': el frontend no muestra burbuja (solo descarta '' y 'NO_CLARO')",
             f"el frontend mostraria una burbuja con {s!r}")
        c.note(f"'{words}' -> {st} {brief(r)} ({ms:.0f} ms)")


# ----------------------------------------------------------------------------- CU-03

def _wav(b64):
    raw = base64.b64decode(b64)
    with wave.open(io.BytesIO(raw)) as w:
        return raw, w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes() / w.getframerate()


@tc("TC-LSA-003-01")
def sintesis(base):
    c = base.c
    need_voices()
    rate = json.loads((base.tree / "voices" / "es_AR-daniela-high.onnx.json").read_text(encoding="utf-8"))["audio"]["sample_rate"]
    st, r, _ = ps(base, "dolor")
    c.eq(st, 200, "HTTP de 'dolor'")
    c.ok(bool(r.get("audio_base64")), "audio_base64 no vacio", "vacio")
    raw, ch, sw, fr, dur = _wav(r["audio_base64"])
    c.ok(raw[:4] == b"RIFF" and raw[8:12] == b"WAVE", 'bytes comienzan con "RIFF" y "WAVE"', raw[:12])
    c.ok(ch == 1 and sw == 2 and fr == rate, f"mono, 16 bits, {rate} Hz", f"canales={ch} bytes/muestra={sw} Hz={fr}")
    c.ok(dur > 0.3, "duracion > 0.3 s", f"{dur:.2f} s")
    st, r2, _ = ps(base, "cabeza dolor respirar yo")
    dur2 = _wav(r2["audio_base64"])[4]
    c.ok(dur2 > dur, "el audio de la frase larga dura mas que 'Tengo dolor.'", f"{dur2:.2f} s vs {dur:.2f} s")
    c.note(f"'Tengo dolor.': WAV mono 16 bits {fr} Hz, {dur:.2f} s, {len(raw)} bytes; frase larga {dur2:.2f} s")


@tc("TC-LSA-003-02")
def cache_audio(base):
    c = base.c
    need_voices()
    _, a, ms_a = ps(base, "cabeza dolor respirar yo")
    _, b, ms_b = ps(base, "cabeza dolor respirar yo")
    c.ok(bool(a.get("audio_base64")) and a["latency_ms"] > 100, "1ra respuesta con audio y latency_ms > 100", f"latency_ms={a.get('latency_ms')}")
    c.eq(b.get("audio_base64"), a.get("audio_base64"), "audio_base64 identico en la repeticion")
    c.ok(b.get("latency_ms", 999) <= 50, "repeticion con latency_ms <= 50", b.get("latency_ms"))
    _, d, _ = ps(base, "yo cabeza dolor")
    _, e, _ = ps(base, "dolor yo cabeza")
    c.ok(d.get("natural_sentence") == e.get("natural_sentence") == "Me duele la cabeza.", "ambas dan 'Me duele la cabeza.'",
         (d.get("natural_sentence"), e.get("natural_sentence")))
    c.eq(e.get("audio_base64"), d.get("audio_base64"), "mismo audio_base64 en ambas secuencias")
    c.ok(e.get("latency_ms", 999) <= 50, "segunda secuencia con latency_ms <= 50", e.get("latency_ms"))
    c.note(f"latency_ms: sintesis={a.get('latency_ms')} (cliente {ms_a:.0f} ms), repeticion={b.get('latency_ms')}, "
           f"'yo cabeza dolor'={d.get('latency_ms')}, 'dolor yo cabeza'={e.get('latency_ms')}")


@tc("TC-LSA-003-03", srv="tree")
def sin_piper(base):
    c = base.c
    need_voices()
    import shutil
    shutil.rmtree(base.tree / "voices")
    with server(base.tree, base.db) as b:
        log = b.log.read_text(encoding="utf-8", errors="replace")
        c.ok("Piper TTS Model not found" in log, 'log "[Nexora] Piper TTS Model not found"', short(log, 200))
        st, r, _ = ps(b, "dolor")
        c.eq(st, 200, "HTTP de 'dolor' sin Piper")
        c.eq(r.get("natural_sentence"), "Tengo dolor.", "natural_sentence")
        c.eq(r.get("audio_base64"), "", "audio_base64")
        c.ok("error" not in r and "detail" not in r, "sin error", brief(r))
        m = wait_for(lambda: http(b, "GET", "/metrics")[1]["counts"].get("sentence"), 5)
        c.eq(m, 1, "counts.sentence")
        st, h = http(b, "GET", "/")
        c.eq(st, 200, "servicio operativo (GET /)")
        c.note(f"sin voices/: {st} {brief(r)}; counts.sentence={m}; GET / -> {short(h)}")
