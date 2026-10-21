from app import _is_faithful


def test_fidelity_accepts_faithful_sentences():
    assert _is_faithful("Me duele la cabeza.", "yo dolor cabeza")
    assert _is_faithful("Tengo dolor de cabeza.", "yo dolor cabeza idle")
    assert _is_faithful("Me cuesta respirar.", "yo respirar")
    assert _is_faithful("Me duele el brazo.", "yo dolor brazo")


def test_fidelity_rejects_prompt_leaks():
    assert not _is_faithful("Me duele el brazo. (NO agregues fiebre)", "yo dolor brazo")
    assert not _is_faithful("Traducción: Me duele el brazo.", "yo dolor brazo")


def test_fidelity_rejects_added_content():
    assert not _is_faithful("Tengo fiebre y dolor de cabeza.", "yo dolor cabeza")
    assert not _is_faithful("No tengo dolor.", "yo dolor")
    assert not _is_faithful("Tengo dolor desde hace 3 días.", "yo dolor")
    assert not _is_faithful("Mi hijo tiene dolor.", "dolor")
    assert not _is_faithful("Tengo mucho dolor.", "yo dolor")
    assert not _is_faithful("Ayúdenme, tengo dolor.", "yo dolor")


def test_fidelity_rejects_more_than_one_sentence():
    assert not _is_faithful("Me duele. Tengo dolor.", "yo dolor")
