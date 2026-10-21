"""Usage: python tests/api/run_all.py [TC-LSA-001-02 | 001-02 ...]   (no args = every API case)
Run it twice in a row to detect flaky cases: the second run records the first one in `corrida_anterior`."""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import harness
import test_reconocimiento, test_traduccion, test_captura, test_entrenamiento  # noqa: F401,E401
import test_reportes, test_auditoria, test_privacidad, test_rendimiento  # noqa: F401,E401

ids = [a if a.startswith("TC-") else f"TC-LSA-{a}" for a in sys.argv[1:]] or None
res = harness.run(ids)
print({s: sum(r["status"] == s for r in res) for s in ("pass", "fail", "blocked")})
sys.exit(any(r["status"] == "fail" for r in res))
