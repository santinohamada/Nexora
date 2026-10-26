"""CU-06 / CU-07 backend: POST /capture, GET /classes, GET /dataset_stats. Corren sobre una copia temporal del arbol."""
import json
import math
import os
import time

import numpy as np

from harness import tc, http, sample, ws_open, ws_window, snapshot, short

L = "zz_tc_006"


def fr(n, lm=75, vals=4):
    return np.zeros((n, lm, vals)).tolist()


def cap(base, label=L, frames=None, **extra):
    body = {"label": label, "recorder": "test", "frames": fr(5) if frames is None else frames, **extra}
    return http(base, "POST", "/capture", body)


def listing(base, *parts):
    d = os.path.join(base.tree, *parts)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


@tc("TC-LSA-006-05")
def validaciones_capture(base):
    c = base.c
    st, r = cap(base, frames=fr(4))
    c.ok(st == 400 and r == {"detail": "Too few frames (min 5)"}, "4 frames -> 400 Too few frames (min 5)", f"{st} {short(r)}")
    c.note(f"4 frames -> {st} {short(r)}")
    st, r = cap(base, blendshapes=[[0.1] * 52] * 5)
    sep_ok = r.get("saved_to", "").replace("\\", "/")
    ok = (st == 200 and r.get("status") == "ok" and r.get("samples_for_label") == 1
          and sep_ok.startswith(f"dataset/custom/{L}/") and sep_ok.endswith(".npy"))
    c.ok(ok, 'HTTP 200 {"status":"ok","saved_to":"dataset/custom/zz_tc_006/<timestamp>.npy","samples_for_label":1}', f"{st} {short(r)}")
    c.ok(len(listing(base, "dataset", "custom", L)) == 1 and len(listing(base, "dataset", "custom_blendshapes", L)) == 1,
         "archivos en dataset/custom/zz_tc_006 y dataset/custom_blendshapes/zz_tc_006",
         (listing(base, "dataset", "custom", L), listing(base, "dataset", "custom_blendshapes", L)))
    c.note(f"5 frames + blendshapes -> {st} {short(r)} (en Windows saved_to usa separadores mixtos: dataset/custom\...); "
           f"custom/{L}={listing(base, 'dataset', 'custom', L)} custom_blendshapes/{L}={listing(base, 'dataset', 'custom_blendshapes', L)}")
    bad = fr(5)
    bad[2][10][1] = float("nan")
    st, r = cap(base, frames=bad, blendshapes=[[0.0] * 52] * 5)
    c.ok(st == 400 and r == {"detail": "Non-finite frame value"}, "NaN -> 400 Non-finite frame value", f"{st} {short(r)}")
    c.note(f"NaN -> {st} {short(r)}")
    for name, extra, want in [("sin blendshapes", {}, "Missing blendshapes"),
                              ("con 4 filas para 5 frames", {"blendshapes": [[0.0] * 52] * 4}, "Blendshapes frame count mismatch"),
                              ("con filas de 51 valores", {"blendshapes": [[0.0] * 51] * 5}, "Blendshapes row must have 52 values")]:
        st, r = cap(base, **extra)
        c.ok(st == 400 and r == {"detail": want}, f"{name} -> 400 {want}", f"{st} {short(r)}")
        c.note(f"{name} -> {st} {short(r)}")


@tc("TC-LSA-006-06")
def persistencia(base):
    c = base.c
    src = sample("yo")
    before = snapshot(base.tree)
    t_ms = time.time() * 1000
    st, r = cap(base, frames=src.tolist(), blendshapes=[[0.1] * 52] * 45)
    c.eq(st, 200, "HTTP de la primera captura")
    path = os.path.join(base.tree, r["saved_to"])
    arr = np.load(path)
    c.ok(arr.shape == (45, 75, 4) and arr.dtype == np.float32 and np.allclose(arr, src),
         "shape (45,75,4), float32 y valores iguales a los enviados", f"shape={arr.shape} dtype={arr.dtype} allclose={np.allclose(arr, src)}")
    stem = os.path.splitext(os.path.basename(path))[0]
    c.ok(stem.isdigit() and abs(int(stem) - t_ms) < 60000, "nombre <ms epoch>.npy", stem)
    time.sleep(0.01)
    st, r2 = cap(base, frames=src.tolist(), blendshapes=[[0.1] * 52] * 45)
    c.eq(r2.get("samples_for_label"), 2, "samples_for_label tras la segunda captura")
    st, ds = http(base, "GET", "/dataset_stats")
    c.eq(ds.get(L), 2, f"/dataset_stats[{L}]")
    after = snapshot(base.tree)
    new = sorted(k for k in after if k not in before)
    c.ok(len(new) == 4 and all(k.endswith(".npy") for k in new), "solo 4 archivos .npy nuevos (2 de landmarks y 2 de blendshapes; sin video, imagen ni audio)", new)
    c.note(f"archivo guardado {stem}.npy shape={arr.shape} dtype={arr.dtype}; samples_for_label=2; dataset_stats[{L}]={ds.get(L)}; "
           f"archivos nuevos: {new}")


@tc("TC-LSA-006-07")
def forma_invalida(base):
    c = base.c
    before = snapshot(base.tree)
    st, r = cap(base, frames=[[[0.0, 0.0], [0.0, 0.0]]] * 5)
    new = sorted(k for k in snapshot(base.tree) if k not in before)
    c.ok(st == 400 and not new, "frames (5,2,2) -> 400 y ningun archivo creado", f"{st} {short(r)}; archivos creados: {new}")
    c.note(f"(5,2,2) -> {st} {short(r)}; archivos creados: {new}")
    ragged = [[[0.0] * 4] * (1 + i % 3) for i in range(5)]
    st, r = cap(base, frames=ragged)
    c.ok(st == 400, "listas irregulares -> 400 (y no 500)", f"{st} {short(r)}")
    c.note(f"irregulares -> {st} {short(r)}")
    st, r = http(base, "POST", "/predict", {"frames": fr(6, lm=3)})
    c.ok(st == 400, "POST /predict con (6,3,4) -> 400", f"{st} {short(r)}")
    c.note(f"/predict (6,3,4) -> {st} {short(r)}")
    ok = sample("dolor")
    with ws_open(base, "?v=1") as ws:
        r = ws_window(ws, np.zeros((6, 3, 4)))
        c.ok(isinstance(r, dict) and "error" in r, "/ws/predict con ventana invalida -> mensaje {\"error\": ...}", short(r))
        c.note(f"WS (6,3,4) -> {short(r)}")
        r = ws_window(ws, ok)
        c.eq(r.get("sign"), "dolor", "la conexion sigue abierta y clasifica una muestra valida")
        nan = ok.copy()
        nan[3, 5, 1] = np.nan
        r = ws_window(ws, nan)
        conf = r.get("confidence")
        rejected = "error" in r or not (isinstance(conf, float) and math.isnan(conf))
        c.ok(rejected and "error" in r, "ventana con NaN rechazada, sin confidence NaN", short(r))
        c.note(f"WS con un NaN -> {short(r)}")


@tc("TC-LSA-007-01")
def clases_y_stats(base):
    c = base.c
    classes = json.loads((base.tree / "models" / "custom_classes.json").read_text(encoding="utf-8"))
    st, r = http(base, "GET", "/classes")
    c.ok(st == 200 and r == ["cabeza", "dolor", "idle", "respirar", "yo"] == classes,
         '/classes = ["cabeza","dolor","idle","respirar","yo"] = models/custom_classes.json', f"{st} {r}")
    st, r = http(base, "GET", "/dataset_stats")
    want = {k: 30 for k in ("cabeza", "dolor", "idle", "respirar", "yo")}
    c.ok(st == 200 and r == want, f"/dataset_stats = {want}", f"{st} {r}")
    c.note(f"/classes -> {classes}; /dataset_stats -> {r}")
    os.makedirs(base.tree / "dataset" / "custom" / "zz_tc_007")
    (base.tree / "dataset" / "custom" / "suelto.txt").write_text("x")
    st, r = http(base, "GET", "/dataset_stats")
    c.ok(r.get("zz_tc_007") == 0 and "suelto.txt" not in r, 'aparece "zz_tc_007": 0 y se ignora el archivo suelto', r)
    c.note(f"con carpeta vacia y archivo suelto -> {r}")


@tc("TC-LSA-007-04")
def patron_etiqueta(base):
    c = base.c
    before = snapshot(base.tree)
    for label in ("a", "a_1", "z" * 32):
        st, r = cap(base, label=label, blendshapes=[[0.0] * 52] * 5)
        c.eq(st, 200, f"HTTP con label de {len(label)} caracteres")
        c.note(f"label {label[:8]!r} ({len(label)} car.) -> {st}")
    for label in ("z" * 33, "", "Dolor", "zz probe", "dolor!", "../x", "ñ"):
        st, r = cap(base, label=label)
        c.ok(st == 400 and r == {"detail": "Invalid label"}, f"label {label!r} -> 400 Invalid label", f"{st} {short(r)}")
        c.note(f"label {label[:10]!r} ({len(label)} car.) -> {st} {short(r)}")
    new = sorted(k for k in snapshot(base.tree) if k not in before)
    c.ok(all(k.startswith(("dataset/custom/", "dataset/custom_blendshapes/")) for k in new) and len(new) == 6,
         "solo 6 archivos nuevos (landmarks y blendshapes), todos bajo dataset/ (\"../x\" no escribe fuera)", new)
    c.note(f"archivos creados: {len(new)} -> {new}")
