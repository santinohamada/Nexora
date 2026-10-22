import os
import tempfile

import app
from capture_validation import validate_recorder


def test_recorder_validation():
    assert validate_recorder(None) is None and validate_recorder("") is None
    assert validate_recorder("Santi-2") == "santi-2"
    for bad in ("a_b", "../x", "a/b", "a\b", "a.b", "a b", "x" * 33):
        try:
            validate_recorder(bad)
            assert False, f"expected ValueError for {bad!r}"
        except ValueError:
            pass


def test_capture_respects_dataset_dir_and_recorder():
    saved = app.DATASET_DIR, app.RECORDER
    try:
        for recorder in (None, "santi"):
            with tempfile.TemporaryDirectory() as tmp:
                app.DATASET_DIR, app.RECORDER = tmp, recorder
                payload = app.CapturePayload(label="zz_rec", frames=[[[0.0] * 4] * 75] * 5, blendshapes=[[0.0] * 52] * 5)
                assert app.capture(payload)["samples_for_label"] == 1
                for sub in ("custom", "custom_blendshapes"):
                    (name,) = os.listdir(os.path.join(tmp, sub, "zz_rec"))
                    assert name.endswith(f"_{recorder}.npy" if recorder else ".npy"), name
                    assert ("_" in name) == bool(recorder), name
                assert app.dataset_stats() == {"zz_rec": 1}
    finally:
        app.DATASET_DIR, app.RECORDER = saved


if __name__ == "__main__":
    test_recorder_validation()
    test_capture_respects_dataset_dir_and_recorder()
    print("test_capture_recorder: all assertions passed")
