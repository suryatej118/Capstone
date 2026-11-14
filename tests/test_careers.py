
from unittest.mock import Mock

from backend.enrichment.careers import detect_careers_page


def test_detects_careers_url(monkeypatch):
    monkeypatch.setattr(
        "backend.enrichment.careers.extract_urls",
        lambda text: ["https://example.com/careers"],
    )

    result = detect_careers_page(
        "Apply here: https://example.com/careers"
    )

    assert result["present"] is True
    assert result["url"] == "https://example.com/careers"
    assert result["method"] == "url"


def test_careers_keyword_alone_is_not_verified_evidence():
    text = "Join our team and explore exciting career opportunities."

    result = detect_careers_page(text)

    assert result["present"] is False
    assert result["url"] is None
    assert result["method"] == "keyword_mention"


def test_returns_false_without_careers_evidence(monkeypatch):
    monkeypatch.setattr(
        "backend.enrichment.careers.extract_urls",
        lambda text: [],
    )

    result = detect_careers_page("A general message with no hiring details.")

    assert result["present"] is False
    assert result["url"] is None
    assert result["method"] == "none"


def test_handles_empty_text():
    result = detect_careers_page("")

    assert result["present"] is False
    assert result["url"] is None
    assert result["method"] == "none"


def test_verifies_careers_page_on_company_website(monkeypatch):
    response = Mock()
    response.status_code = 200
    response.url = "https://example.com/careers"
    response.text = "Careers and job opportunities at Example Company"

    monkeypatch.setattr(
        "backend.enrichment.careers.extract_urls",
        lambda text: [],
    )
    monkeypatch.setattr(
        "backend.enrichment.careers.requests.get",
        lambda *args, **kwargs: response,
    )

    result = detect_careers_page(
        "We are hiring at Example Company.",
        domain="example.com",
    )

    assert result["present"] is True
    assert result["url"] == "https://example.com/careers"
    assert result["method"] == "website"
