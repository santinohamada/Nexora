"""Minimal API test harness: isolated runtime tree, server lifecycle, @tc registry, runner, WS helper.
Deps: stdlib + numpy + websockets (already in venv).

Isolation: every case runs against a TEMP COPY of the runtime tree (app.py, models, dataset, ...) and a temp
SQLite file, so nothing a case writes (captures, trained models, DB rows) can reach the real repo."""
import contextlib, glob, json, math, os, platform, shutil, socket, sqlite3, subprocess, sys, tempfile, time
import traceback, urllib.error, urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from websockets.sync.client import connect  # noqa: F401  (re-exported for tests)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = Path(__file__).parent / "results" / "api-results.json"
CASES = {}  # id -> (fn, mode)
RUNTIME = ("app.py", "storage.py", "capture_validation.py", "train_lstm.py", "eval_model.py",
           "src", "models", "voices", "dataset")


class Blocked(Exception):
    """Raise inside a test when it cannot run (missing dependency, etc.)."""


class Check:
    """Collects observations (notes) and expectation mismatches (fails) without stopping at the first one."""

    def __init__(self):
        self.notes, self.fails, self.n = [], [], 0

    def note(self, text):
        self.notes.append(str(text))

    def ok(self, cond, expected, observed):
        self.n += 1
        if not cond:
            self.fails.append(f"Esperado: {expected}. Observado: {observed}")
        return bool(cond)

    def eq(self, got, want, what):
        return self.ok(got == want, f"{what} = {want!r}", repr(got))


class Base(str):
    """Backend base URL (str) + the isolated tree/db/log it runs on + the Check of the running case."""
    tree = db = log = None
    c = None


def tc(case_id, srv="server"):
    """srv='server': fresh backend per case, fn(base). srv='tree': only the isolated tree+db, the test starts
    its own backend(s) with server(base.tree, base.db)."""
    def deco(fn):
        CASES[case_id] = (fn, srv)
        return fn
    return deco


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_tree(dest):
    """Copy the runtime files into dest. voices/ (read-only, 109 MB) is hard-linked when possible."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    ign = shutil.ignore_patterns("__pycache__", "*.pyc")

    def link_or_copy(src, dst):
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    # dataset/ is copied from git-tracked files only: new captures or zz_* labels left by other tools must not leak into the runtime.
    tracked = subprocess.run(["git", "ls-files", "-z", "dataset/custom", "dataset/custom_blendshapes"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    for rel in sorted(set(filter(None, tracked.split(chr(0))))):
        if (ROOT / rel).is_file():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest / rel)
    for name in RUNTIME:
        src = ROOT / name
        if name == "dataset" and tracked:
            continue
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=ign, copy_function=link_or_copy if name == "voices" else shutil.copy2)
        elif src.exists():
            shutil.copy2(src, dest / name)
    return dest


@contextmanager
def server(tree, db, env=None, timeout=180):
    """Start uvicorn (cwd=tree, NEXORA_DB_PATH=db) on a free port; yield Base; stop."""
    port = free_port()
    e = {**os.environ, "NEXORA_DB_PATH": str(db), "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", **(env or {})}
    logpath = Path(db).parent / f"uvicorn-{port}.log"
    log = open(logpath, "w", encoding="utf-8")
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(port)],
                         cwd=str(tree), env=e, stdout=log, stderr=subprocess.STDOUT)
    base = Base(f"http://127.0.0.1:{port}")
    base.tree, base.db, base.log = Path(tree), str(db), logpath
    try:
        end = time.time() + timeout
        while time.time() < end:
            if p.poll() is not None:
                raise RuntimeError("uvicorn exited:\n" + logpath.read_text(encoding="utf-8", errors="replace"))
            try:
                urllib.request.urlopen(base + "/metrics", timeout=2)
                break
            except Exception:
                time.sleep(0.4)
        else:
            raise RuntimeError("server not ready")
        yield base
    finally:
        p.terminate()
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            p.kill()
        log.close()


def http(base, method, path, body=None, headers=None, full=False, timeout=60):
    """Returns (status, parsed_json_or_text); with full=True (status, headers, parsed)."""
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"} if data else {}
    h.update(headers or {})
    req = urllib.request.Request(base + path, data=data, method=method, headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as err:
        r = err
    raw = r.read().decode(errors="replace")
    try:
        parsed = json.loads(raw)
    except ValueError:
        parsed = raw
    return (r.code, dict(r.headers), parsed) if full else (r.code, parsed)


def sample(label, idx=0, name=None):
    """Load dataset/custom/<label>/<name or idx-th>.npy from the REAL repo (read-only) -> (T,75,4) float32."""
    d = ROOT / "dataset" / "custom" / label
    path = d / f"{name}.npy" if name else sorted(glob.glob(str(d / "*.npy")))[idx]
    return np.load(path).astype(np.float32)


def send_sequence(base_or_ws_url, frames, binary=False, timeout=20):
    """Send one window of frames (T,75,4) to /ws/predict, return the prediction dict.
    binary=True -> protocol v2 (?v=2; NOTE: currently broken server-side, see README): 4-byte header (0x02,0,0,0) + float32 LE T*75*4.
    binary=False -> v1 JSON {"frames": [...]}. Server replies with ONE JSON per window:
    {"sign","confidence","top3"} or {"error": ...}."""
    url = base_or_ws_url.replace("http://", "ws://")
    if "/ws/predict" not in url:
        url += "/ws/predict"
    frames = np.asarray(frames, dtype=np.float32)
    with connect(url + ("?v=2" if binary else ""), open_timeout=timeout) as ws:
        if binary:
            ws.send(b"\x02\x00\x00\x00" + frames.tobytes())
        else:
            ws.send(json.dumps({"frames": frames.tolist()}))
        return json.loads(ws.recv(timeout=timeout))


def ws_open(base, query="", **kw):
    return connect(base.replace("http://", "ws://") + "/ws/predict" + query, open_timeout=20, **kw)


def ws_window(ws, frames, timeout=20):
    ws.send(json.dumps({"frames": np.asarray(frames, dtype=np.float32).tolist()}))
    return json.loads(ws.recv(timeout=timeout))


def rows(db, sql, *params):
    conn = sqlite3.connect(db, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def db_bytes(db):
    """Raw bytes of the SQLite file and its -wal/-shm companions."""
    return {suffix or "db": Path(db + suffix).read_bytes() for suffix in ("", "-wal", "-shm") if os.path.exists(db + suffix)}


def snapshot(root):
    out = {}
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in files:
            p = os.path.join(d, f)
            st = os.stat(p)
            out[os.path.relpath(p, root).replace("\\", "/")] = (st.st_size, st.st_mtime_ns)
    return out


def wait_for(fn, timeout=5.0, step=0.1):
    """Poll fn() until truthy (audit rows are written asynchronously after the WS reply)."""
    end = time.time() + timeout
    while True:
        v = fn()
        if v or time.time() > end:
            return v
        time.sleep(step)


def pct(values, p):
    """Nearest-rank percentile, same method as app._percentile."""
    o = sorted(values)
    return o[min(len(o) - 1, max(0, math.ceil(p / 100 * len(o)) - 1))]


def run_cli(base, *args, timeout=900):
    """Run `python <args>` with cwd = the isolated tree. Returns (returncode, combined output)."""
    e = {**os.environ, "NEXORA_DB_PATH": base.db, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    r = subprocess.run([sys.executable, *args], cwd=str(base.tree), env=e, capture_output=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr)


def need_voices():
    """Block the case if the Piper model (voices/, not versioned) is missing from the repo."""
    if not (ROOT / "voices").is_dir():
        raise Blocked("Falta voices/ (modelo Piper, no versionado); no se puede ejecutar el caso.")


def ollama_up():
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


def ollama_warm():
    """Block the case if Ollama is not reachable; otherwise load qwen2:1.5b into memory."""
    if not ollama_up():
        raise Blocked("Ollama no responde en localhost:11434; no se puede ejecutar el caso.")
    req = urllib.request.Request("http://localhost:11434/api/generate", method="POST",
                                 data=json.dumps({"model": "qwen2:1.5b", "prompt": "hola", "stream": False}).encode())
    try:
        urllib.request.urlopen(req, timeout=180).read()
    except Exception as ex:
        raise Blocked(f"No se pudo precalentar qwen2:1.5b en Ollama: {ex}")


def short(x, n=160):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + f"...(+{len(s) - n})"


def _git_hash():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        return "?"


def _cpu():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or "?"
    except Exception:
        return platform.processor()


def environment():
    return {"commit": _git_hash(), "python": platform.python_version(), "os": platform.platform(),
            "cpu": _cpu(), "cpu_count": os.cpu_count()}


@contextmanager
def _case_env(mode):
    with tempfile.TemporaryDirectory(prefix="nexora-test-", ignore_cleanup_errors=True) as tmp:
        tree, db = make_tree(Path(tmp) / "tree"), str(Path(tmp) / "test.db")
        if mode == "tree":
            b = Base("")
            b.tree, b.db = tree, db
            yield b
        else:
            with server(tree, db) as b:
                yield b


def run(ids=None):
    """Run registered cases (all or `ids`), merge into results/api-results.json (keeps the previous run's
    status in `corrida_anterior`, and flags `inestable` when it differs)."""
    env = environment()
    old = {r["id"]: r for r in json.loads(RESULTS.read_text(encoding="utf-8"))} if RESULTS.exists() else {}
    new = {}
    for cid, (fn, mode) in CASES.items():
        if ids and cid not in ids:
            continue
        t0, stamp, status = time.time(), datetime.now(timezone.utc).isoformat(timespec="seconds"), "pass"
        c, extra = Check(), ""
        try:
            with _case_env(mode) as b:
                b.c = c
                ret = fn(b)
                if ret is not None:
                    c.note(short(ret, 300))
        except Blocked as ex:
            status, extra = "blocked", str(ex)
        except Exception as ex:
            status = "fail"
            extra = "ERROR DE EJECUCION: " + "".join(traceback.format_exception_only(type(ex), ex)).strip()[:600]
        if status == "pass" and c.fails:
            status = "fail"
        if status == "pass" and c.n == 0:
            status, extra = "fail", "ERROR DE EJECUCION: sin verificaciones (el caso no evaluo ninguna expectativa)"
        observed = "; ".join(c.notes)
        if c.fails:
            observed += " || DISCREPANCIAS: " + " ; ".join(c.fails)
        if extra:
            observed += (" || " if observed else "") + extra
        rec = {"id": cid, "status": status, "observed": observed, "duration_s": round(time.time() - t0, 2),
               "timestamp": stamp, "environment": env}
        prev = old.get(cid)
        if prev and prev.get("environment", {}).get("commit") == env["commit"]:  # only same-commit runs are comparable
            rec["corrida_anterior"] = prev["status"]
            rec["inestable"] = prev["status"] != status
        else:
            rec["corrida_anterior"], rec["inestable"] = None, None
        new[cid] = rec
        print(f"{status.upper():8} {cid}  ({rec['duration_s']}s)  {observed[:300]}", flush=True)
    merged = {**old, **new}
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps([merged[k] for k in sorted(merged)], indent=2, ensure_ascii=False, default=str),
                       encoding="utf-8")
    return list(new.values())
