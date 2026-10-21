import json
import os
import sqlite3
import tempfile
import threading
from datetime import datetime, timedelta, timezone

import capture_validation
import storage


def _fresh_db() -> str:
    path = os.path.join(tempfile.mkdtemp(), "test.db")
    storage.init_db(path)
    return path


def test_save_report_persists_message_words_and_report():
    db = _fresh_db()
    saved = storage.save_report(
        db, text="Tengo dolor de cabeza.", station="paciente", words=["dolor", "cabeza"], client_message_id=111
    )
    assert saved["new_message"] is True

    conn = sqlite3.connect(db)
    assert conn.execute("SELECT text FROM reported_message").fetchone()[0] == "Tengo dolor de cabeza."
    assert conn.execute("SELECT word FROM recognized_word ORDER BY position").fetchall() == [("dolor",), ("cabeza",)]
    assert conn.execute("SELECT message_id, station FROM translation_report").fetchone() == (
        saved["message_id"],
        "paciente",
    )
    conn.close()


def test_same_message_reported_from_both_stations_reuses_message():
    db = _fresh_db()
    first = storage.save_report(db, text="Necesito agua.", station="paciente", words=None, client_message_id=7)
    second = storage.save_report(db, text="Necesito agua.", station="recepcion", words=None, client_message_id=7)
    assert first["message_id"] == second["message_id"]
    assert second["new_message"] is False

    summary = storage.report_summary(db)
    assert summary["total_reports"] == 2
    assert summary["top_messages"][0] == {
        "text": "Necesito agua.",
        "reports": 2,
        "last_reported_at": summary["top_messages"][0]["last_reported_at"],
    }


def test_report_without_client_id_creates_new_message_each_time():
    db = _fresh_db()
    a = storage.save_report(db, text="Hola.", station="paciente", words=None, client_message_id=None)
    b = storage.save_report(db, text="Hola.", station="paciente", words=None, client_message_id=None)
    assert a["message_id"] != b["message_id"]


def test_schema_rejects_invalid_station():
    db = _fresh_db()
    try:
        storage.save_report(db, text="Hola.", station="guardia", words=None, client_message_id=None)
        assert False, "expected IntegrityError"
    except sqlite3.IntegrityError:
        pass
    # The failed transaction must not leave an orphan message behind.
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM reported_message").fetchone()[0] == 0
    conn.close()


def test_top_words_ranks_by_report_count():
    db = _fresh_db()
    storage.save_report(db, text="Me duele la cabeza.", station="paciente", words=["doler", "cabeza"], client_message_id=1)
    storage.save_report(db, text="Cabeza mareo.", station="paciente", words=["cabeza", "mareo"], client_message_id=2)
    words = storage.report_summary(db)["top_words"]
    assert words[0] == {"word": "cabeza", "reports": 2}


def test_audit_metrics_counts_and_since_filter():
    db = _fresh_db()
    storage.log_audit_event(db, "consent", station="paciente", consent="accepted")
    storage.log_audit_event(db, "sentence", translation_ms=10.5, tts_ms=20.0, total_ms=31.0, source="template", word_count=2)
    storage.log_audit_event(db, "report", station="recepcion")

    metrics = storage.audit_metrics(db)
    assert metrics["counts"] == {"consent": 1, "sentence": 1, "report": 1}
    assert metrics["consent"] == {"accepted": 1, "declined": 0}
    assert metrics["sources"] == {"template": 1}
    assert metrics["latency_samples"]["total_ms"] == [31.0]

    future = datetime.now(timezone.utc) + timedelta(hours=1)
    assert storage.audit_metrics(db, future)["counts"] == {}


def test_schema_rejects_unknown_audit_type():
    db = _fresh_db()
    try:
        storage.log_audit_event(db, "frames", station="paciente")
        assert False, "expected IntegrityError"
    except sqlite3.IntegrityError:
        pass


def test_concurrent_reports_of_same_message_do_not_race():
    db = _fresh_db()
    n = 8
    barrier = threading.Barrier(n)
    errors, results = [], []

    def worker():
        try:
            barrier.wait()
            results.append(
                storage.save_report(
                    db, text="Dolor fuerte.", station="paciente", words=["dolor", "fuerte"], client_message_id=42
                )
            )
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len({r["message_id"] for r in results}) == 1
    assert sum(r["new_message"] for r in results) == 1
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM reported_message").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM translation_report").fetchone()[0] == n
    assert conn.execute("SELECT word FROM recognized_word ORDER BY position").fetchall() == [("dolor",), ("fuerte",)]
    conn.close()


def test_report_message_id_range():
    ok = capture_validation.validate_report_payload
    ok("Hola.", "paciente", None, 1_760_000_000_000)  # Date.now()-sized
    ok("Hola.", "paciente", None, None)
    ok("Hola.", "paciente", None, 2**53 - 1)
    for bad in (-1, 2**53, 2**63, 10**30, True, 1.5):
        try:
            ok("Hola.", "paciente", None, bad)
            assert False, f"expected ValueError for {bad!r}"
        except ValueError:
            pass


def test_migrate_jsonl_skips_bad_rows_and_is_idempotent():
    db = _fresh_db()
    d = tempfile.mkdtemp()
    reports, audit = os.path.join(d, "reports.jsonl"), os.path.join(d, "audit.jsonl")
    with open(reports, "w", encoding="utf-8") as f:
        f.write(json.dumps({"text": "Hola.", "station": "paciente", "words": ["hola"], "timestamp": "2026-09-24T18:18:28-03:00"}) + "\n")
        f.write(json.dumps({"text": "Agua.", "station": "recepcion", "words": None, "timestamp": "2026-09-24T21:18:29+00:00"}) + "\n")
        f.write("[1, 2]\n")  # not a dict
        f.write("{not json\n")  # malformed
        f.write(json.dumps({"text": "Mal.", "station": "paciente", "words": [""]}) + "\n")  # empty word
        f.write(json.dumps({"text": "Mal.", "station": "paciente", "words": ["x" * 33]}) + "\n")  # too-long word
        f.write(json.dumps({"text": "Mal.", "station": "guardia"}) + "\n")  # invalid station
    with open(audit, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "consent", "timestamp": "2026-09-24T21:18:28+00:00", "station": "paciente", "consent": "accepted"}) + "\n")
        f.write(json.dumps({"type": "frames"}) + "\n")
        f.write(json.dumps({"type": "sentence", "total_ms": "fast"}) + "\n")

    assert storage.migrate_jsonl(db, reports, audit) == {"reports": 2, "audit_events": 1, "skipped": 7}
    assert not os.path.exists(reports) and os.path.exists(reports + ".migrated")
    assert not os.path.exists(audit) and os.path.exists(audit + ".migrated")
    assert storage.migrate_jsonl(db, reports, audit) == {"reports": 0, "audit_events": 0, "skipped": 0}

    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM reported_message").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM audit_event").fetchone()[0] == 1
    # Offset timestamps are normalized to UTC.
    assert conn.execute("SELECT first_reported_at FROM reported_message ORDER BY id").fetchone()[0] == "2026-09-24T21:18:28.000000+00:00"
    conn.close()


def test_audit_failure_is_swallowed_by_best_effort_wrapper_only():
    # Mirrors app._log_audit (app.py needs the models loaded, so it cannot be imported here).
    bad_db = os.path.join(tempfile.mkdtemp(), "missing_dir", "x.db")  # never initialized, dir missing

    def best_effort(event_type, **fields):
        try:
            storage.log_audit_event(bad_db, event_type, **fields)
        except Exception:  # noqa: BLE001
            return False
        return True

    assert best_effort("report", station="paciente") is False
    try:
        storage.log_audit_event(bad_db, "report", station="paciente")
        assert False, "strict path must raise"
    except sqlite3.Error:
        pass


def test_init_db_widens_old_audit_type_check_keeping_rows():
    db = _fresh_db()
    conn = sqlite3.connect(db)
    old = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'audit_event'").fetchone()[0].replace(", 'reply_sent'", "")
    conn.executescript("DROP TABLE audit_event;" + old)
    conn.execute("INSERT INTO audit_event (type, occurred_at, station) VALUES ('fin_atencion', 'x', 'recepcion')")
    conn.commit()
    conn.close()

    storage.init_db(db)
    storage.log_audit_event(db, "reply_sent", station="recepcion")
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT type FROM audit_event ORDER BY id").fetchall() == [("fin_atencion",), ("reply_sent",)]
    conn.close()


def test_default_db_path_is_anchored_to_module_dir():
    if "NEXORA_DB_PATH" not in os.environ:
        assert os.path.isabs(storage.DEFAULT_DB_PATH)
        assert os.path.dirname(os.path.dirname(storage.DEFAULT_DB_PATH)) == os.path.dirname(os.path.abspath(storage.__file__))


if __name__ == "__main__":
    test_save_report_persists_message_words_and_report()
    test_same_message_reported_from_both_stations_reuses_message()
    test_report_without_client_id_creates_new_message_each_time()
    test_schema_rejects_invalid_station()
    test_top_words_ranks_by_report_count()
    test_audit_metrics_counts_and_since_filter()
    test_schema_rejects_unknown_audit_type()
    test_concurrent_reports_of_same_message_do_not_race()
    test_report_message_id_range()
    test_migrate_jsonl_skips_bad_rows_and_is_idempotent()
    test_audit_failure_is_swallowed_by_best_effort_wrapper_only()
    test_init_db_widens_old_audit_type_check_keeping_rows()
    test_default_db_path_is_anchored_to_module_dir()
    print("test_storage: all assertions passed")
