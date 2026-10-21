"""RNF-01 / RNF-01.1: latencia del backend. Cada cifra es una mediana/p95 de varias corridas."""
import itertools
import statistics
import time
from pathlib import Path

from harness import (tc, http, server, sample, ws_open, ws_window, pct, wait_for, ollama_warm, environment, short)

TOK = ["cabeza", "dolor", "respirar", "yo"]
_ENV = {}


def hw(base_url=None):
    if not _ENV:
        _ENV.update(environment())
    dev = http(base_url, "GET", "/")[1].get("device") if base_url else "?"
    return f"CPU {_ENV['cpu']} ({_ENV['cpu_count']} hilos), dispositivo del modelo: {dev}"


def stats(v):
    return f"p50={statistics.median(v):.0f} p95={pct(v, 95):.0f} max={max(v):.0f} (n={len(v)})"


def near(a, b):
    return abs(a - b) <= max(0.05 * b, 1.5)


@tc("TC-LSA-014-01", srv="tree")
def plantillas(base):
    c = base.c
    combos = [" ".join(x) for n in range(1, 5) for x in itertools.combinations(TOK, n)]
    pooled, pooled_all, per_run, mm = [], [], [], []
    hwtxt = ""
    for run in range(3):
        db = str(Path(base.db).with_name(f"run{run}.db"))
        with server(base.tree, db) as b:
            hwtxt = hwtxt or hw(b)
            seen, lat_all, lat_new, cli = set(), [], [], []
            for w in combos:
                t0 = time.perf_counter()
                st, r = http(b, "POST", "/process_sentence", {"words": w})
                cli.append((time.perf_counter() - t0) * 1000)
                assert st == 200 and r["source"] == "template", (w, st, r)
                lat_all.append(r["latency_ms"])
                if r["natural_sentence"] not in seen:
                    lat_new.append(r["latency_ms"])
                seen.add(r["natural_sentence"])
            m = http(b, "GET", "/metrics")[1]["latency_ms"]["total_ms"]
        pooled += lat_new
        pooled_all += lat_all
        per_run.append(f"corrida {run + 1}: latency_ms sin cache de audio {stats(lat_new)}; cliente {stats(cli)}")
        mm.append((m, lat_all, cli))
    c.ok(statistics.median(pooled) <= 600, "p50 de latency_ms <= 600 ms", f"{statistics.median(pooled):.0f} ms")
    c.ok(pct(pooled, 95) <= 1000, "p95 de latency_ms <= 1000 ms", f"{pct(pooled, 95):.0f} ms")
    for i, (m, lat, cli) in enumerate(mm, 1):
        c.ok(near(m["p50"], pct(lat, 50)) and near(m["p95"], pct(lat, 95)),
             f"corrida {i}: total_ms de /metrics coincide (5 %) con latency_ms de las respuestas",
             f"/metrics p50={m['p50']} p95={m['p95']} vs respuestas p50={pct(lat, 50)} p95={pct(lat, 95)}")
    c.note(f"3 corridas con backend reiniciado, 15 combinaciones por corrida (13 oraciones distintas sin cache de audio; "
           f"2 repiten oracion). Agrupado sin cache: {stats(pooled)}; todas: {stats(pooled_all)}. " + " | ".join(per_run) +
           f". /metrics total_ms: {[(m['p50'], m['p95'], m['max']) for m, _, _ in mm]} (p50,p95,max). "
           f"El tiempo del cliente incluye HTTP y base64 y supera a latency_ms. Hardware: {hwtxt}. Otro proceso (pruebas UI) pudo compartir CPU.")


@tc("TC-LSA-014-02")
def inferencia_ws(base):
    c = base.c
    wins = [sample(l, i) for l in ("cabeza", "dolor", "idle", "respirar", "yo") for i in range(20)]
    labels = [l for l in ("cabeza", "dolor", "idle", "respirar", "yo") for _ in range(20)]
    rtt, errors, wrong = [], 0, 0
    with ws_open(base, "?v=1") as ws:
        for i in range(200):
            t0 = time.perf_counter()
            r = ws_window(ws, wins[i % 100])
            rtt.append((time.perf_counter() - t0) * 1000)
            errors += "error" in r
            wrong += r.get("sign") != labels[i % 100]
    c.eq(errors, 0, "errores en 200 ventanas")
    c.ok(pct(rtt, 95) < 1000, "p95 de ida y vuelta < 1000 ms", f"{pct(rtt, 95):.1f} ms")
    wait_for(lambda: http(base, "GET", "/metrics")[1]["latency_ms"].get("lstm_ms", {}).get("count") == 200, 10)
    m = http(base, "GET", "/metrics")[1]["latency_ms"].get("lstm_ms")
    c.ok(bool(m) and m["count"] == 200, "lstm_ms registrado para las 200 ventanas", m)
    first, last = pct(rtt[:50], 95), pct(rtt[-50:], 95)
    c.ok(last <= 2 * first, "p95 de las ultimas 50 <= 2 x el de las primeras 50", f"primeras {first:.1f} ms, ultimas {last:.1f} ms")
    c.note(f"200 ventanas por una conexion: ida y vuelta p50={statistics.median(rtt):.1f} p95={pct(rtt, 95):.1f} max={max(rtt):.1f} ms; "
           f"0 desconexiones; /metrics lstm_ms={m} (linea base); p95 primeras 50={first:.1f} ms, ultimas 50={last:.1f} ms; "
           f"ventanas mal clasificadas (muestras de entrenamiento)={wrong}. Hardware: {hw(base)}")


PHRASES = ["yo dolor pecho", "yo dolor brazo", "fiebre tos", "yo mareo", "yo dolor estomago", "yo dolor garganta",
           "yo nauseas", "tos fuerte", "yo dolor espalda", "yo dolor pierna"]


@tc("TC-LSA-014-03", srv="tree")
def ruta_ollama(base):
    c = base.c
    ollama_warm()
    pooled, per_run, srcs, mm = [], [], [], []
    hwtxt = ""
    for run in range(3):
        db = str(Path(base.db).with_name(f"run{run}.db"))
        with server(base.tree, db) as b:
            hwtxt = hwtxt or hw(b)
            lat = []
            for w in PHRASES:
                st, r = http(b, "POST", "/process_sentence", {"words": w}, timeout=60)
                assert st == 200, (w, st, r)
                lat.append(r["latency_ms"])
                srcs.append(r["source"] + ("" if r["natural_sentence"] != w else "(reserva)"))
            m = http(b, "GET", "/metrics")[1]["latency_ms"]
        pooled += lat
        mm.append((m, lat))
        per_run.append(f"corrida {run + 1}: {stats(lat)}")
    c.ok(pct(pooled, 95) <= 1000, "p95 de latency_ms <= 1000 ms (meta del caso general de RNF-01.1)",
         f"p50={statistics.median(pooled):.0f} ms, p95={pct(pooled, 95):.0f} ms, max={max(pooled)} ms")
    for i, (m, lat) in enumerate(mm, 1):
        t = m.get("total_ms", {})
        c.ok(bool(t) and near(t["p50"], pct(lat, 50)) and near(t["p95"], pct(lat, 95)),
             f"corrida {i}: /metrics reporta los mismos percentiles que las respuestas", f"/metrics {t} vs respuestas p50={pct(lat, 50)} p95={pct(lat, 95)}")
    c.note(f"3 corridas x 10 combinaciones sin plantilla, Ollama precalentado (qwen2:1.5b), backend reiniciado por corrida (cache vacia). "
           f"Agrupado {stats(pooled)}. " + " | ".join(per_run) +
           f". Fuentes: {sorted(set(srcs))} ({srcs.count('ollama')} ollama). /metrics translation_ms/total_ms por corrida: "
           f"{[(m.get('translation_ms', {}).get('p50'), m.get('translation_ms', {}).get('p95'), m.get('total_ms', {}).get('p95')) for m, _ in mm]}. Hardware: {hwtxt}")
