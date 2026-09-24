from capture_validation import validate_report_payload


def test_report_accepts_valid_payload():
    validate_report_payload("Tengo dolor de cabeza.", "paciente", ["dolor", "cabeza"])


def test_report_accepts_valid_payload_without_words():
    validate_report_payload("Tengo dolor de cabeza.", "recepcion", None)


def test_report_rejects_empty_text():
    try:
        validate_report_payload("", "paciente", None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_report_rejects_whitespace_only_text():
    try:
        validate_report_payload("   ", "paciente", None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_report_rejects_text_too_long():
    try:
        validate_report_payload("a" * 501, "paciente", None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_report_rejects_bad_station():
    try:
        validate_report_payload("Tengo dolor.", "enfermeria", None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_report_rejects_too_many_words():
    try:
        validate_report_payload("Tengo dolor.", "paciente", ["dolor"] * 21)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_report_rejects_empty_word():
    try:
        validate_report_payload("Tengo dolor.", "paciente", ["dolor", ""])
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    test_report_accepts_valid_payload()
    test_report_accepts_valid_payload_without_words()
    test_report_rejects_empty_text()
    test_report_rejects_whitespace_only_text()
    test_report_rejects_text_too_long()
    test_report_rejects_bad_station()
    test_report_rejects_too_many_words()
    test_report_rejects_empty_word()
    print("test_report_validation: all assertions passed")
