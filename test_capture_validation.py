from capture_validation import validate_capture_blendshapes


def test_legacy_mode_skips_validation():
    assert validate_capture_blendshapes("legacy", 45, None) is None


def test_tasks_mode_requires_blendshapes():
    try:
        validate_capture_blendshapes("tasks", 45, None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_tasks_mode_frame_count_mismatch():
    try:
        validate_capture_blendshapes("tasks", 45, [[0.0] * 52 for _ in range(10)])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_tasks_mode_wrong_row_length():
    rows = [[0.0] * 52 for _ in range(45)]
    rows[10] = [0.0] * 51
    try:
        validate_capture_blendshapes("tasks", 45, rows)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_tasks_mode_non_finite_value():
    rows = [[0.0] * 52 for _ in range(45)]
    rows[0][0] = float("nan")
    try:
        validate_capture_blendshapes("tasks", 45, rows)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_tasks_mode_valid_payload():
    rows = [[0.1] * 52 for _ in range(45)]
    arr = validate_capture_blendshapes("tasks", 45, rows)
    assert arr.shape == (45, 52)


if __name__ == "__main__":
    test_legacy_mode_skips_validation()
    test_tasks_mode_requires_blendshapes()
    test_tasks_mode_frame_count_mismatch()
    test_tasks_mode_wrong_row_length()
    test_tasks_mode_non_finite_value()
    test_tasks_mode_valid_payload()
    print("test_capture_validation: all assertions passed")
