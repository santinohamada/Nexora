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
import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from capture_validation import validate_report_payload

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = os.environ.get("NEXORA_DB_PATH", str(BASE_DIR / "data" / "lsa_salud.db"))

AUDIT_EVENT_TYPES = (
    "prediction",
    "sentence",
    "report",
    "consent",
    "translation_displayed",
    "fin_atencion",
    "reply_sent",
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


def _migrate_audit_event_types(conn) -> None:
    """Databases created before a type was added keep the old CHECK; rebuild the table once to widen it.

    The rebuild runs in one IMMEDIATE transaction (SQLite DDL is transactional), so a crash rolls
    back to the old table and a concurrent startup waits for the lock, then sees the widened schema.
    """
    def widened() -> bool:
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'audit_event'").fetchone()["sql"]
        return all(f"'{t}'" in sql for t in AUDIT_EVENT_TYPES)

    if widened():
        return
    conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    if widened():
        return  # another process migrated it while we waited; _connect commits
    new_sql = _SCHEMA.split("CREATE TABLE IF NOT EXISTS audit_event", 1)[1].split(");", 1)[0]
    for stmt in (
        "ALTER TABLE audit_event RENAME TO audit_event_old",
        f"CREATE TABLE audit_event{new_sql})",
        "INSERT INTO audit_event SELECT * FROM audit_event_old",
        "DROP TABLE audit_event_old",
        "CREATE INDEX IF NOT EXISTS idx_audit_event_type_time ON audit_event(type, occurred_at)",
    ):
        conn.execute(stmt)


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(_SCHEMA)
        _migrate_audit_event_types(conn)


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
        # Atomic insert-or-ignore: stations reporting the same message concurrently cannot race.
        # A NULL client_message_id never conflicts (NULLs are distinct in UNIQUE), so it always inserts.
        cur = conn.execute(
            "INSERT INTO reported_message (client_message_id, text, first_reported_at) VALUES (?, ?, ?) "
            "ON CONFLICT(client_message_id, text) DO NOTHING",
            (client_message_id, text, now),
        )
        is_new_message = cur.rowcount == 1
        if is_new_message:
            message_id = cur.lastrowid
            if words:
                conn.executemany(
                    "INSERT INTO recognized_word (message_id, position, word) VALUES (?, ?, ?)",
                    [(message_id, pos, word) for pos, word in enumerate(words)],
                )
        else:
            message_id = conn.execute(
                "SELECT id FROM reported_message WHERE client_message_id = ? AND text = ?",
                (client_message_id, text),
            ).fetchone()["id"]

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


def _legacy_ts(value) -> str:
    """Normalize a legacy timestamp to the module's ISO UTC format; raises ValueError if unparseable."""
    if value is None:
        return utc_now_iso()
    if not isinstance(value, str):
        raise ValueError("bad timestamp")
    return to_utc_iso(datetime.fromisoformat(value))


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def migrate_jsonl(db_path: str, reports_path: str, audit_path: str) -> dict:
    """One-off import of the legacy logs/*.jsonl files.

    Idempotent: once the import commits, each source file is renamed to `<name>.migrated`, so a
    second run finds nothing to import. Rows that are malformed, not JSON objects, or have invalid
    fields (same rules as the API) are skipped and counted in `skipped`; they never abort the
    import. Legacy timestamps are normalized to ISO UTC so the lexicographic `since` filter works.
    """
    imported = {"reports": 0, "audit_events": 0, "skipped": 0}

    def _lines(path):
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    imported["skipped"] += 1
                    continue
                if isinstance(rec, dict):
                    yield rec
                else:
                    imported["skipped"] += 1

    with _connect(db_path) as conn:
        for rec in _lines(reports_path):
            text, station, words = rec.get("text"), rec.get("station"), rec.get("words")
            try:
                if not isinstance(text, str) or not isinstance(station, str):
                    raise ValueError("bad field type")
                if words is not None and (not isinstance(words, list) or not all(isinstance(w, str) for w in words)):
                    raise ValueError("bad words")
                validate_report_payload(text, station, words)
                ts = _legacy_ts(rec.get("timestamp"))
            except ValueError:
                imported["skipped"] += 1
                continue
            cur = conn.execute(
                "INSERT INTO reported_message (client_message_id, text, first_reported_at) VALUES (NULL, ?, ?)",
                (text, ts),
            )
            message_id = cur.lastrowid
            for pos, word in enumerate(words or []):
                conn.execute(
                    "INSERT INTO recognized_word (message_id, position, word) VALUES (?, ?, ?)",
                    (message_id, pos, word),
                )
            conn.execute(
                "INSERT INTO translation_report (message_id, station, reported_at) VALUES (?, ?, ?)",
                (message_id, station, ts),
            )
            imported["reports"] += 1

        for rec in _lines(audit_path):
            columns = ["type", "occurred_at"]
            try:
                if rec.get("type") not in AUDIT_EVENT_TYPES:
                    raise ValueError("bad type")
                values = [rec["type"], _legacy_ts(rec.get("timestamp"))]
                for name in AUDIT_TEXT_FIELDS + AUDIT_NUMERIC_FIELDS + AUDIT_INT_FIELDS:
                    v = rec.get(name)
                    if v is None:
                        continue
                    if name in AUDIT_NUMERIC_FIELDS:
                        ok = _is_number(v)
                    elif name in AUDIT_INT_FIELDS:
                        ok = isinstance(v, int) and not isinstance(v, bool)
                    elif name == "station":
                        ok = v in ("paciente", "recepcion")
                    elif name == "consent":
                        ok = v in ("accepted", "declined")
                    else:
                        ok = isinstance(v, str)
                    if not ok:
                        raise ValueError(f"bad {name}")
                    columns.append(name)
                    values.append(v)
            except ValueError:
                imported["skipped"] += 1
                continue
            conn.execute(
                f"INSERT INTO audit_event ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
            imported["audit_events"] += 1

    # Only reached if the transaction committed.
    for path in (reports_path, audit_path):
        if os.path.exists(path):
            os.replace(path, path + ".migrated")
    print(f"migrate_jsonl: {imported['skipped']} rows skipped")
    return imported


if __name__ == "__main__":
    init_db()
    result = migrate_jsonl(
        DEFAULT_DB_PATH,
        str(BASE_DIR / "logs" / "reports.jsonl"),
        str(BASE_DIR / "logs" / "audit.jsonl"),
    )
    print(f"Migrated into {DEFAULT_DB_PATH}: {result}")
