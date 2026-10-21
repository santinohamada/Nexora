"""CU-08 y RNF-02: train_lstm.py y eval_model.py por linea de comandos, sobre una copia temporal del arbol
(el entrenamiento sobrescribe models/lstm.pth y models/custom_classes.json)."""
import os
import re
import shutil
import time

from harness import tc, http, server, run_cli, sample, ws_open, ws_window, snapshot, short


@tc("TC-LSA-008-01", srv="tree")
def entrenar(base):
    c = base.c
    t0 = time.time()
    rc, out = run_cli(base, "train_lstm.py")
    el = time.time() - t0
    c.eq(rc, 0, "codigo de salida de train_lstm.py")
    m = re.search(r"Trained on (\d+) samples\. Model saved to (models[\\/]lstm\.pth)", out)
    c.ok(bool(m) and m.group(1) == "150", 'cierre "Trained on 150 samples. Model saved to models/lstm.pth"', short(out[-200:]))
    c.note(f"entrenamiento {el:.0f} s, rc={rc}; ruta impresa={m.group(2) if m else None} (en Windows con barra invertida)")
    pth, cls = base.tree / "models" / "lstm.pth", base.tree / "models" / "custom_classes.json"
    c.ok(pth.exists() and pth.stat().st_mtime >= t0 and cls.stat().st_mtime >= t0,
         "models/lstm.pth y custom_classes.json existen con fecha actualizada",
         f"pth existe={pth.exists()}, classes mtime>=inicio={cls.stat().st_mtime >= t0}")
    with server(base.tree, base.db) as b:
        log = b.log.read_text(encoding="utf-8", errors="replace")
        loaded = re.search(r"Custom LSTM Model loaded.*5 classes.*", log)
        c.ok(bool(loaded), 'log "Custom LSTM Model loaded ... 5 classes"', short(log, 300))
        st, classes = http(b, "GET", "/classes")
        st2, health = http(b, "GET", "/")
        c.ok(classes == ["cabeza", "dolor", "idle", "respirar", "yo"] and health.get("classes") == 5,
             "/classes con las 5 clases y GET / classes = 5", f"{classes} {health}")
        res = {}
        with ws_open(b, "?v=1") as ws:
            for label in classes:
                r = ws_window(ws, sample(label, 0))
                res[label] = (r.get("sign"), r.get("confidence"))
                c.eq(r.get("sign"), label, f"clasificacion de una muestra de {label}")
        c.note(f"modelo cargado: {loaded.group(0)[:120] if loaded else None}; clasificacion por clase (muestras de entrenamiento): {res}")


@tc("TC-LSA-008-02", srv="tree")
def sin_datos(base):
    c = base.c
    models = base.tree / "models"
    snap0 = snapshot(models)
    shutil.rmtree(base.tree / "dataset" / "custom")
    rc, out = run_cli(base, "train_lstm.py", timeout=300)
    c.ok(rc == 0 and out.strip() == "Dataset path dataset/custom not found. Por favor graba algunos datos primero.",
         'imprime "Dataset path dataset/custom not found. Por favor graba algunos datos primero." y termina sin error', f"rc={rc} {short(out)}")
    c.note(f"sin dataset/custom -> rc={rc} salida={short(out)}")
    os.makedirs(base.tree / "dataset" / "custom")
    rc, out = run_cli(base, "train_lstm.py", timeout=300)
    c.ok(rc == 0 and out.strip() == "No se encontraron clases en el dataset. Por favor graba algunos datos primero.",
         'imprime "No se encontraron clases en el dataset. Por favor graba algunos datos primero."', f"rc={rc} {short(out)}")
    c.note(f"dataset/custom vacia -> rc={rc} salida={short(out)}")
    c.ok(snapshot(models) == snap0, "ningun archivo de models/ creado ni modificado", "models/ cambio")
    c.note(f"models/ sin cambios: {sorted(snap0)}")


@tc("TC-LSA-015-01", srv="tree")
def evaluar(base):
    c = base.c
    os.makedirs(base.tree / "dataset" / "vacio")
    rc, out = run_cli(base, "eval_model.py", "dataset/custom", timeout=300)
    warn = ("ADVERTENCIA: evaluando sobre dataset/custom, el mismo dataset usado para entrenar. "
            "La accuracy resultante no mide generalización real.")
    c.ok(warn in out, "advertencia de evaluacion sobre el conjunto de entrenamiento", short(out[:300]))
    c.ok("Muestras evaluadas: 150 (MAX_FRAMES=45)" in out, '"Muestras evaluadas: 150 (MAX_FRAMES=45)"',
         re.findall(r"Muestras evaluadas:.*", out))
    m = re.search(r"Accuracy global: (\d+\.\d+)%", out)
    c.ok(bool(m) and float(m.group(1)) >= 90, "Accuracy global >= 90 %", m.group(0) if m else "no impresa")
    c.ok(bool(re.search(r"Clase\s+Precision\s+Recall\s+Support", out)), "tabla Clase/Precision/Recall/Support", "ausente")
    c.ok("Matriz de confusión" in out, "matriz de confusion", "ausente")
    umbral = " | ".join(re.findall(r"Muestras bajo umbral.*", out))
    tabla = " / ".join(l.strip() for l in out.splitlines() if re.match(r"(cabeza|dolor|idle|respirar|yo)\s+\d", l))
    c.note(f"rc={rc}; {m.group(0) if m else 'sin accuracy'}; {umbral}; tabla: {tabla}. "
           "Evalua sobre el conjunto de entrenamiento: no mide generalizacion.")
    for arg, want in [("dataset/no_existe", "Directorio no encontrado: dataset/no_existe"),
                      ("dataset/vacio", "No se encontraron muestras .npy en dataset/vacio")]:
        rc, out = run_cli(base, "eval_model.py", arg, timeout=300)
        c.ok(want in out, f'"{want}"', short(out[-200:]))
        c.note(f"{arg} -> rc={rc} '{want if want in out else short(out[-120:])}'")
    rc, out = run_cli(base, "eval_model.py", timeout=300)
    c.ok("Uso: python eval_model.py <directorio_dataset>" in out, '"Uso: python eval_model.py <directorio_dataset>"', short(out[-200:]))
    c.note(f"sin argumentos -> rc={rc} '{out.strip().splitlines()[-1] if out.strip() else ''}'")
