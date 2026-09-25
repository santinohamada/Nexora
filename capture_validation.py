import math
import re

import numpy as np

BLENDSHAPE_COUNT = 52
LABEL_PATTERN = re.compile(r"[a-z0-9_]{1,32}")

REPORT_TEXT_MAX_LEN = 500
REPORT_STATIONS = {"paciente", "recepcion"}
REPORT_WORDS_MAX_COUNT = 20
REPORT_WORD_MAX_LEN = 32

AUDIT_TYPES = {"consent", "translation_displayed"}
AUDIT_STATIONS = {"paciente", "recepcion"}
AUDIT_CONSENT_VALUES = {"accepted", "declined"}
AUDIT_E2E_MS_MAX = 60000


def validate_capture_label(label: str) -> None:
    if not LABEL_PATTERN.fullmatch(label):
        raise ValueError("Invalid label")


def validate_capture_blendshapes(mode: str, frame_count: int, blendshapes):
    if mode != "tasks":
        return None
    if blendshapes is None:
        raise ValueError("Missing blendshapes for tasks mode")
    if len(blendshapes) != frame_count:
        raise ValueError("Blendshapes frame count mismatch")
    if any(len(row) != BLENDSHAPE_COUNT for row in blendshapes):
        raise ValueError("Blendshapes row must have 52 values")
    arr = np.array(blendshapes, dtype=np.float32)
    if not np.isfinite(arr).all():
        raise ValueError("Non-finite blendshapes value")
    return arr


def validate_report_payload(text: str, station: str, words: list[str] | None) -> None:
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
