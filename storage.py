"""SQLite persistence for structured records: translation reports and audit events.

Training samples (.npy), the recognition model (.pth) and the Piper voice (.onnx)
stay on the filesystem: they are binary artifacts consumed natively by numpy and
PyTorch. This module only stores structured, queryable records.

The conversation itself is NOT persisted (RNF-03.1). The only message content that
reaches disk is the text of a message explicitly reported as an incorrect or
ambiguous translation (RF-06.1), stored in `reported_message`.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DEFAULT_DB_PATH = os.environ.get("NEXORA_DB_PATH", os.path.join("data", "lsa_salud.db"))

AUDIT_EVENT_TYPES = (
    "prediction",
    "sentence",
    "report",
    "consent",
    "translation_displayed",
    "fin_atencion",
)
AUDIT_NUMERIC_FIELDS = ("lstm_ms", "confidence", "translation_ms", "tts_ms", "total_ms", "e2e_ms")
AUDIT_LATENCY_FIELDS = ("lstm_ms", "translation_ms", "tts_ms", "total_ms", "e2e_ms")
AUDIT_TEXT_FIELDS = ("station", "consent", "source")
AUDIT_INT_FIELDS = ("word_count",)

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS reported_message (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    client_message_id INTEGER,
    text              TEXT    NOT NULL CHECK (length(text) BETWEEN 1 AND 500),
    first_reported_at TEXT    NOT NULL,
    UNIQUE (client_message_id, text)
);

CREATE TABLE IF NOT EXISTS recognized_word (
    message_id INTEGER NOT NULL REFERENCES reported_message(id) ON DELETE CASCADE,
    position   INTEGER NOT NULL CHECK (position >= 0),
    word       TEXT    NOT NULL CHECK (length(word) BETWEEN 1 AND 32),
    PRIMARY KEY (message_id, position)
);

CREATE TABLE IF NOT EXISTS translation_report (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id  INTEGER NOT NULL REFERENCES reported_message(id) ON DELETE CASCADE,
    station     TEXT    NOT NULL CHECK (station IN ('paciente', 'recepcion')),
    reported_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_translation_report_message ON translation_report(message_id);

CREATE TABLE IF NOT EXISTS audit_event (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    type           TEXT    NOT NULL CHECK (type IN ({", ".join(f"'{t}'" for t in AUDIT_EVENT_TYPES)})),
    occurred_at    TEXT    NOT NULL,
    station        TEXT    CHECK (station IS NULL OR station IN ('paciente', 'recepcion')),
    consent        TEXT    CHECK (consent IS NULL OR consent IN ('accepted', 'declined')),
    lstm_ms        REAL,
    confidence     REAL,
    translation_ms REAL,
    tts_ms         REAL,
    total_ms       REAL,
    e2e_ms         REAL,
    source         TEXT,
    word_count     INTEGER
);
CREATE INDEX IF NOT EXISTS idx_audit_event_type_time ON audit_event(type, occurred_at);
"""


def utc_now_iso() -> str:
    """Fixed-width ISO 8601 UTC timestamp, so lexicographic order equals chronological order."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


@contextmanager
def _connect(db_path: str):
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:  # commits on success, rolls back on exception
            yield conn
    finally:
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(_SCHEMA)


def save_report(
    db_path: str,
    *,
    text: str,
    station: str,
    words: list[str] | None,
    client_message_id: int | None,
) -> dict:
    """Persist a translation report and the reported message (reused if already reported)."""
    now = utc_now_iso()
    with _connect(db_path) as conn:
        row = None
        if client_message_id is not None:
            row = conn.execute(
                "SELECT id FROM reported_message WHERE client_message_id = ? AND text = ?",
                (client_message_id, text),
            ).fetchone()

        if row is not None:
            message_id = row["id"]
            is_new_message = False
        else:
            cur = conn.execute(
                "INSERT INTO reported_message (client_message_id, text, first_reported_at) VALUES (?, ?, ?)",
                (client_message_id, text, now),
            )
            message_id = cur.lastrowid
            is_new_message = True
            if words:
                conn.executemany(
                    "INSERT INTO recognized_word (message_id, position, word) VALUES (?, ?, ?)",
                    [(message_id, pos, word) for pos, word in enumerate(words)],
                )

        cur = conn.execute(
            "INSERT INTO translation_report (message_id, station, reported_at) VALUES (?, ?, ?)",
            (message_id, station, now),
        )
        return {"report_id": cur.lastrowid, "message_id": message_id, "new_message": is_new_message}


def log_audit_event(db_path: str, event_type: str, **fields) -> None:
    columns = ["type", "occurred_at"]
    values: list = [event_type, utc_now_iso()]
    for name in AUDIT_TEXT_FIELDS + AUDIT_NUMERIC_FIELDS + AUDIT_INT_FIELDS:
        if fields.get(name) is not None:
            columns.append(name)
            values.append(fields[name])
    placeholders = ", ".join("?" for _ in columns)
    with _connect(db_path) as conn:
        conn.execute(
            f"INSERT INTO audit_event ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )


def audit_metrics(db_path: str, since: datetime | None = None) -> dict:
    """Aggregate audit events; percentiles are computed by the caller from the raw samples."""
    where, params = "", []
    if since is not None:
        where, params = "WHERE occurred_at >= ?", [to_utc_iso(since)]

    with _connect(db_path) as conn:
        counts = {
            r["type"]: r["n"]
            for r in conn.execute(f"SELECT type, COUNT(*) AS n FROM audit_event {where} GROUP BY type", params)
        }
        consent = {"accepted": 0, "declined": 0}
        consent_where = f"{where} {'AND' if where else 'WHERE'} type = 'consent' AND consent IS NOT NULL"
        for r in conn.execute(
            f"SELECT consent, COUNT(*) AS n FROM audit_event {consent_where} GROUP BY consent", params
        ):
            consent[r["consent"]] = r["n"]

        source_where = f"{where} {'AND' if where else 'WHERE'} type = 'sentence' AND source IS NOT NULL"
        sources = {
            r["source"]: r["n"]
            for r in conn.execute(
                f"SELECT source, COUNT(*) AS n FROM audit_event {source_where} GROUP BY source", params
            )
        }

        latency_samples: dict[str, list[float]] = {}
        for field in AUDIT_LATENCY_FIELDS:
            field_where = f"{where} {'AND' if where else 'WHERE'} {field} IS NOT NULL"
            latency_samples[field] = [
                r[0] for r in conn.execute(f"SELECT {field} FROM audit_event {field_where}", params)
            ]

    return {"counts": counts, "consent": consent, "sources": sources, "latency_samples": latency_samples}


def report_summary(db_path: str, limit: int = 10) -> dict:
    """Most reported messages and recognized words, as input for retraining prioritization (CU-08)."""
    with _connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM translation_report").fetchone()[0]
        messages = [
            {"text": r["text"], "reports": r["n"], "last_reported_at": r["last_at"]}
            for r in conn.execute(
                """
                SELECT m.text, COUNT(r.id) AS n, MAX(r.reported_at) AS last_at
                FROM reported_message m
                JOIN translation_report r ON r.message_id = m.id
                GROUP BY m.id
                ORDER BY n DESC, last_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        ]
        words = [
            {"word": r["word"], "reports": r["n"]}
            for r in conn.execute(
                """
                SELECT w.word, COUNT(r.id) AS n
                FROM recognized_word w
                JOIN translation_report r ON r.message_id = w.message_id
                GROUP BY w.word
                ORDER BY n DESC, w.word
                LIMIT ?
                """,
                (limit,),
            )
        ]
    return {"total_reports": total, "top_messages": messages, "top_words": words}


def migrate_jsonl(db_path: str, reports_path: str, audit_path: str) -> dict:
    """One-off import of the legacy logs/*.jsonl files. Malformed lines are skipped."""
    imported = {"reports": 0, "audit_events": 0}

    def _lines(path):
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    with _connect(db_path) as conn:
        for rec in _lines(reports_path):
            if not rec.get("text") or rec.get("station") not in ("paciente", "recepcion"):
                continue
            ts = rec.get("timestamp") or utc_now_iso()
            cur = conn.execute(
                "INSERT INTO reported_message (client_message_id, text, first_reported_at) VALUES (NULL, ?, ?)",
                (rec["text"][:500], ts),
            )
            message_id = cur.lastrowid
            for pos, word in enumerate(rec.get("words") or []):
                conn.execute(
                    "INSERT INTO recognized_word (message_id, position, word) VALUES (?, ?, ?)",
                    (message_id, pos, str(word)[:32]),
                )
            conn.execute(
                "INSERT INTO translation_report (message_id, station, reported_at) VALUES (?, ?, ?)",
                (message_id, rec["station"], ts),
            )
            imported["reports"] += 1

        for rec in _lines(audit_path):
            if rec.get("type") not in AUDIT_EVENT_TYPES:
                continue
            columns = ["type", "occurred_at"]
            values = [rec["type"], rec.get("timestamp") or utc_now_iso()]
            for name in AUDIT_TEXT_FIELDS + AUDIT_NUMERIC_FIELDS + AUDIT_INT_FIELDS:
                if rec.get(name) is not None:
                    columns.append(name)
                    values.append(rec[name])
            conn.execute(
                f"INSERT INTO audit_event ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
            imported["audit_events"] += 1

    return imported


if __name__ == "__main__":
    init_db()
    result = migrate_jsonl(
        DEFAULT_DB_PATH,
        os.path.join("logs", "reports.jsonl"),
        os.path.join("logs", "audit.jsonl"),
    )
    print(f"Migrated into {DEFAULT_DB_PATH}: {result}")
