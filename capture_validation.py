import math
import os
import re

import numpy as np

BLENDSHAPE_COUNT = 52
FRAME_LANDMARKS = 75
FRAME_VALUES = 4  # x, y, z, visibility
LABEL_PATTERN = re.compile(r"[a-z0-9_]{1,32}")
# Shared dataset root (e.g. a Google Drive for desktop synced folder); landmarks live in <root>/custom, blendshapes in <root>/custom_blendshapes.
DATASET_DIR = os.environ.get("NEXORA_DATASET_DIR") or "dataset"
# No "_" so the "<timestamp>_<recorder>.npy" suffix stays unambiguous; no separators or dots (it goes into a file path).
RECORDER_PATTERN = re.compile(r"[a-z0-9-]{1,32}")

REPORT_TEXT_MAX_LEN = 500
REPORT_MESSAGE_ID_MAX = 2**53 - 1  # JS Number.MAX_SAFE_INTEGER; Date.now() ids are far below
REPORT_STATIONS = {"paciente", "recepcion"}
REPORT_WORDS_MAX_COUNT = 20
REPORT_WORD_MAX_LEN = 32

AUDIT_TYPES = {"consent", "translation_displayed", "fin_atencion", "reply_sent"}
AUDIT_STATIONS = {"paciente", "recepcion"}
AUDIT_CONSENT_VALUES = {"accepted", "declined"}
AUDIT_E2E_MS_MAX = 60000


def validate_capture_label(label: str) -> None:
    if not LABEL_PATTERN.fullmatch(label):
        raise ValueError("Invalid label")


def validate_recorder(recorder):
    """Return the lowercased recorder name, or None when unset/empty; raise ValueError if it is not [A-Za-z0-9-]{1,32}."""
    if not recorder:
        return None
    recorder = recorder.lower()
    if not RECORDER_PATTERN.fullmatch(recorder):
        raise ValueError(f"Invalid NEXORA_RECORDER {recorder!r}: use only letters, digits and '-' (1-32 chars)")
    return recorder


def validate_frames(frames) -> np.ndarray:
    """Return frames as a finite float32 array of shape (T, 75, 4); raise ValueError otherwise."""
    try:
        arr = np.array(frames, dtype=np.float32)
    except (ValueError, TypeError):  # ragged or non-numeric
        raise ValueError("Invalid frames shape; expected (T, 75, 4)")
    if arr.ndim != 3 or arr.shape[1:] != (FRAME_LANDMARKS, FRAME_VALUES):
        raise ValueError("Invalid frames shape; expected (T, 75, 4)")
    if not np.isfinite(arr).all():
        raise ValueError("Non-finite frame value")
    return arr


def validate_capture_blendshapes(frame_count: int, blendshapes):
    if blendshapes is None:
        raise ValueError("Missing blendshapes")
    if len(blendshapes) != frame_count:
        raise ValueError("Blendshapes frame count mismatch")
    if any(len(row) != BLENDSHAPE_COUNT for row in blendshapes):
        raise ValueError("Blendshapes row must have 52 values")
    arr = np.array(blendshapes, dtype=np.float32)
    if not np.isfinite(arr).all():
        raise ValueError("Non-finite blendshapes value")
    return arr


def validate_report_payload(
    text: str, station: str, words: list[str] | None, message_id: int | None = None
) -> None:
    if message_id is not None:
        if not isinstance(message_id, int) or isinstance(message_id, bool):
            raise ValueError("Invalid message_id")
        if not 0 <= message_id <= REPORT_MESSAGE_ID_MAX:
            raise ValueError("Invalid message_id")
    if not text or not text.strip():
        raise ValueError("Empty text")
    if len(text) > REPORT_TEXT_MAX_LEN:
        raise ValueError("Text too long")
    if station not in REPORT_STATIONS:
        raise ValueError("Invalid station")
    if words is not None:
        if len(words) > REPORT_WORDS_MAX_COUNT:
            raise ValueError("Too many words")
        if any(not w or len(w) > REPORT_WORD_MAX_LEN for w in words):
            raise ValueError("Invalid word")


def validate_audit_payload(
    event_type: str, station: str, consent: str | None, e2e_ms: float | None
) -> None:
    if event_type not in AUDIT_TYPES:
        raise ValueError("Invalid audit type")
    if station not in AUDIT_STATIONS:
        raise ValueError("Invalid station")
    if event_type == "consent":
        if consent not in AUDIT_CONSENT_VALUES:
            raise ValueError("Invalid consent value")
    if event_type == "translation_displayed":
        if not isinstance(e2e_ms, (int, float)) or isinstance(e2e_ms, bool):
            raise ValueError("Invalid e2e_ms")
        if not math.isfinite(e2e_ms) or e2e_ms < 0 or e2e_ms > AUDIT_E2E_MS_MAX:
            raise ValueError("Invalid e2e_ms")
