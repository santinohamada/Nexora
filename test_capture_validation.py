from capture_validation import validate_capture_blendshapes, validate_capture_label


def test_label_rejects_path_traversal():
    try:
        validate_capture_label("../x")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_label_rejects_path_separator():
    try:
        validate_capture_label("a/b")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_label_rejects_empty():
    try:
        validate_capture_label("")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_label_rejects_trailing_newline():
    try:
        validate_capture_label("dolor\n")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_label_accepts_valid():
    validate_capture_label("dolor")


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
    test_label_rejects_path_traversal()
    test_label_rejects_path_separator()
    test_label_rejects_empty()
    test_label_rejects_trailing_newline()
    test_label_accepts_valid()
    test_legacy_mode_skips_validation()
    test_tasks_mode_requires_blendshapes()
    test_tasks_mode_frame_count_mismatch()
    test_tasks_mode_wrong_row_length()
    test_tasks_mode_non_finite_value()
    test_tasks_mode_valid_payload()
    print("test_capture_validation: all assertions passed")
