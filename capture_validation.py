import numpy as np

BLENDSHAPE_COUNT = 52


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
