from capture_validation import validate_audit_payload
from app import _latency_summary, _percentile


def test_audit_accepts_consent_accepted():
    validate_audit_payload("consent", "paciente", "accepted", None)


def test_audit_accepts_consent_declined():
    validate_audit_payload("consent", "paciente", "declined", None)


def test_audit_accepts_translation_displayed():
    validate_audit_payload("translation_displayed", "paciente", None, 850.5)


def test_audit_rejects_unknown_type():
    try:
        validate_audit_payload("frames", "paciente", None, None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_audit_rejects_unknown_station():
    try:
        validate_audit_payload("consent", "enfermeria", "accepted", None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_audit_rejects_invalid_consent_value():
    try:
        validate_audit_payload("consent", "paciente", "maybe", None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_audit_rejects_missing_e2e_ms():
    try:
        validate_audit_payload("translation_displayed", "paciente", None, None)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_audit_rejects_negative_e2e_ms():
    try:
        validate_audit_payload("translation_displayed", "paciente", None, -1)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_audit_rejects_non_finite_e2e_ms():
    for value in (float("nan"), float("inf")):
        try:
            validate_audit_payload("translation_displayed", "paciente", None, value)
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_audit_rejects_e2e_ms_out_of_range():
    try:
        validate_audit_payload("translation_displayed", "paciente", None, 999999)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_percentile_matches_known_values():
    values = sorted([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    assert _percentile(values, 50) == 50
    assert _percentile(values, 95) == 100
    assert _percentile(values, 100) == 100


def test_latency_summary_reports_p50_p95_max_count():
    summary = _latency_summary([100, 200, 300, 400, 500])
    assert summary["max"] == 500
    assert summary["count"] == 5
    assert summary["p50"] == 300
    assert summary["p95"] == 500


def test_latency_summary_single_value():
    summary = _latency_summary([42.5])
    assert summary["p50"] == 42.5
    assert summary["p95"] == 42.5
    assert summary["max"] == 42.5
    assert summary["count"] == 1


if __name__ == "__main__":
    test_audit_accepts_consent_accepted()
    test_audit_accepts_consent_declined()
    test_audit_accepts_translation_displayed()
    test_audit_rejects_unknown_type()
    test_audit_rejects_unknown_station()
    test_audit_rejects_invalid_consent_value()
    test_audit_rejects_missing_e2e_ms()
    test_audit_rejects_negative_e2e_ms()
    test_audit_rejects_non_finite_e2e_ms()
    test_audit_rejects_e2e_ms_out_of_range()
    test_percentile_matches_known_values()
    test_latency_summary_reports_p50_p95_max_count()
    test_latency_summary_single_value()
    print("test_audit: all assertions passed")
