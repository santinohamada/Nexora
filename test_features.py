import numpy as np

from src.features import add_hand_local_features


def _sample():
    rng = np.random.RandomState(0)
    x = rng.rand(45, 75, 4).astype(np.float32)
    x[:, 33:54, :2] = -0.3  # left hand absent: constant points
    return x


def test_shape():
    x = _sample()
    assert add_hand_local_features(x).shape == (45, 384)
    assert add_hand_local_features(x, deltas=True).shape == (45, 468)


def test_absent_hand_is_zero():
    out = add_hand_local_features(_sample())
    assert np.all(out[:, 300:342] == 0)
    assert np.any(out[:, 342:384] != 0)


def test_scale_and_translation_invariant():
    x = _sample()
    y = x.copy()
    y[:, 54:75, :2] = y[:, 54:75, :2] * 3.0 + 0.5
    assert np.allclose(add_hand_local_features(x)[:, 342:], add_hand_local_features(y)[:, 342:], atol=1e-4)


def test_deltas_first_frame_zero():
    out = add_hand_local_features(_sample(), deltas=True)
    assert np.all(out[0, 384:] == 0)


if __name__ == "__main__":
    test_shape()
    test_absent_hand_is_zero()
    test_scale_and_translation_invariant()
    test_deltas_first_frame_zero()
    print("test_features: all assertions passed")
