from unittest.mock import Mock

from backend.enrichment.careers import detect_careers_page
from backend.analyzer.hiring_intent import compute_hiring_intent


def test_keyword_only_mention_does_not_award_careers_points():
    text = "Join our team and explore exciting career opportunities."

    result = detect_careers_page(text)
    _, reasons = compute_hiring_intent(
        text,
        {"careers_page_present": result["present"]},
    )
    careers_reason = next(
        item for item in reasons
        if item["signal"] == "careers_page_present"
    )

    assert result["present"] is False
    assert result["method"] == "keyword_mention"
    assert careers_reason["score"] == 0


def test_unverified_careers_url_does_not_award_careers_points(monkeypatch):
    text = "Apply here: https://example.com/careers"
    monkeypatch.setattr(
        "backend.enrichment.careers.extract_urls",
        lambda _: ["https://example.com/careers"],
    )

    result = detect_careers_page(text)
    careers_verified = (
        result.get("present") is True
        and result.get("method") == "website"
        and isinstance(result.get("url"), str)
        and bool(result["url"].strip())
    )
    _, reasons = compute_hiring_intent(
        text,
        {"careers_page_present": careers_verified},
    )
    careers_reason = next(
        item for item in reasons
        if item["signal"] == "careers_page_present"
    )

    assert result["present"] is True
    assert result["method"] == "url"
    assert careers_verified is False
    assert careers_reason["score"] == 0


def test_verified_careers_page_awards_full_points(monkeypatch):
    text = "We are hiring at Example Company."
    response = Mock()
    response.status_code = 200
    response.url = "https://example.com/careers"
    response.text = "Careers and job opportunities at Example Company"

    monkeypatch.setattr(
        "backend.enrichment.careers.extract_urls",
        lambda _: [],
    )
    monkeypatch.setattr(
        "backend.enrichment.careers.requests.get",
        lambda *args, **kwargs: response,
    )

    result = detect_careers_page(text, domain="example.com")
    careers_verified = (
        result.get("present") is True
        and result.get("method") == "website"
        and isinstance(result.get("url"), str)
        and bool(result["url"].strip())
    )
    _, reasons = compute_hiring_intent(
        text,
        {"careers_page_present": careers_verified},
    )
    careers_reason = next(
        item for item in reasons
        if item["signal"] == "careers_page_present"
    )

    assert careers_verified is True
    assert careers_reason["score"] == 20
