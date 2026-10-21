import glob

import numpy as np

from app import _infer


def test_empty_scene_is_idle():
    result, _ = _infer(np.zeros((45, 75, 4), np.float32))
    assert result["sign"] == "idle" and result["confidence"] == 100.0


def test_dataset_samples_classified():
    for label in ("cabeza", "dolor", "idle", "respirar", "yo"):
        sample = np.load(sorted(glob.glob(f"dataset/custom/{label}/*.npy"))[0])
        assert _infer(sample)[0]["sign"] == label, label


def test_short_window_is_not_a_false_sign():
    idle = np.load(sorted(glob.glob("dataset/custom/idle/*.npy"))[0])
    for frames in (5, 20, 30):
        assert _infer(idle[:frames])[0]["sign"] == "idle", frames


if __name__ == "__main__":
    test_empty_scene_is_idle()
    test_dataset_samples_classified()
    test_short_window_is_not_a_false_sign()
    print("ok")
