from backend.enrichment.careers import detect_careers_page

def test_detects_careers_url():
    text = "Apply here: https://acme.com/careers"
    
    result = detect_careers_page(text)

    assert result["present"] is True
    assert result["method"] == "url"


def test_detects_careers_keyword():
    text = "Join our team and explore exciting career opportunities."

    result = detect_careers_page(text)

    assert result["present"] is True
    assert result["method"] == "keyword"


def test_returns_false_without_careers_evidence():
    text = "Acme is hiring a software engineer."

    result = detect_careers_page(text)

    assert result["present"] is False


def test_handles_empty_text():
    result = detect_careers_page("")

    assert result["present"] is False

