import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

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


if __name__ == "__main__":
    test_save_report_persists_message_words_and_report()
    test_same_message_reported_from_both_stations_reuses_message()
    test_report_without_client_id_creates_new_message_each_time()
    test_schema_rejects_invalid_station()
    test_top_words_ranks_by_report_count()
    test_audit_metrics_counts_and_since_filter()
    test_schema_rejects_unknown_audit_type()
    print("test_storage: all assertions passed")
