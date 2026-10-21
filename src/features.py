import numpy as np

HAND_SLOTS = ((33, 54), (54, 75))  # left, right hand landmark ranges in the 75-point layout
ABSENT_SPREAD = 1e-4
EPS = 1e-6
FEATURE_SIZE = 384  # 75 * 4 raw + 84 hand-local, per frame


def hand_present(x: np.ndarray) -> np.ndarray:
    """(T, 2) bool: a hand is present when its 21 points are not all identical in x/y."""
    return np.stack([np.ptp(x[:, a:b, :2], axis=1).max(axis=1) > ABSENT_SPREAD for a, b in HAND_SLOTS], axis=1)


def add_hand_local_features(x: np.ndarray, present=None, deltas: bool = False) -> np.ndarray:
    """(T, 75, 4) -> (T, 300 + 84), or (T, 300 + 168) with per-frame deltas of the local coords.

    Local = x/y relative to the hand wrist (point 0), divided by |wrist -> point 9|; zeros when the
    hand is absent. Pass `present` (T, 2) computed on un-augmented data when x carries noise.
    """
    if present is None:
        present = hand_present(x)
    local = []
    for k, (a, b) in enumerate(HAND_SLOTS):
        xy = x[:, a:b, :2] - x[:, a:a + 1, :2]
        scale = np.linalg.norm(xy[:, 9], axis=1)[:, None, None]
        xy = xy / np.maximum(scale, EPS)
        local.append((xy * present[:, k, None, None]).reshape(len(x), -1))
    local = np.concatenate(local, axis=1).astype(x.dtype)
    parts = [x.reshape(len(x), -1), local]
    if deltas:
        parts.append(np.diff(local, axis=0, prepend=local[:1]))
    return np.concatenate(parts, axis=1)
