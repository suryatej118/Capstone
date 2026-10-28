from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def _mock_enrichment(monkeypatch, careers_result):
    """Keep API tests deterministic and isolate the careers evidence flow."""
    monkeypatch.setattr("backend.main.analyze_rules", lambda text: (0, []))
    monkeypatch.setattr("backend.main.predict_scam_probability", lambda text: 0.2)
    monkeypatch.setattr("backend.main.extract_emails", lambda text: [])
    monkeypatch.setattr("backend.main.extract_domains", lambda text: ["example.com"])
    monkeypatch.setattr("backend.main.extract_company_name", lambda text: "Example Company")
    monkeypatch.setattr("backend.main.get_domain_age_years", lambda domain: None)
    monkeypatch.setattr(
        "backend.main.detect_careers_page",
        lambda text, domain=None: careers_result,
    )
    monkeypatch.setattr(
        "backend.main.get_active_job_postings",
        lambda url: {"count": 0},
    )
    monkeypatch.setattr(
        "backend.main.match_company_name",
        lambda company_name: {"matched": False},
    )
    monkeypatch.setattr("backend.main.extract_github_org", lambda text: None)


def _careers_reason(response_json):
    return next(
        item for item in response_json["hiring_intent_reasons"]
        if item["signal"] == "careers_page_present"
    )


def test_analyze_keyword_mention_does_not_award_careers_points(monkeypatch):
    _mock_enrichment(
        monkeypatch,
        {"present": False, "url": None, "method": "keyword_mention"},
    )

    response = client.post(
        "/analyze",
        json={"text": "Join our team and explore career opportunities."},
    )

    assert response.status_code == 200
    reason = _careers_reason(response.json())
    assert reason["score"] == 0
    assert reason["value"] is False


def test_analyze_unverified_careers_url_does_not_award_careers_points(monkeypatch):
    _mock_enrichment(
        monkeypatch,
        {
            "present": True,
            "url": "https://example.com/careers",
            "method": "url",
        },
    )

    response = client.post(
        "/analyze",
        json={"text": "Apply here: https://example.com/careers"},
    )

    assert response.status_code == 200
    reason = _careers_reason(response.json())
    assert reason["score"] == 0
    assert reason["value"] is False


def test_analyze_verified_careers_page_awards_full_points(monkeypatch):
    _mock_enrichment(
        monkeypatch,
        {
            "present": True,
            "url": "https://example.com/careers",
            "method": "website",
        },
    )

    response = client.post(
        "/analyze",
        json={"text": "We are hiring at Example Company."},
    )

    assert response.status_code == 200
    reason = _careers_reason(response.json())
    assert reason["score"] == 20
    assert reason["value"] is True


def test_analyze_only_checks_job_postings_for_verified_careers_page(monkeypatch):
    calls = []
    _mock_enrichment(
        monkeypatch,
        {
            "present": True,
            "url": "https://example.com/careers",
            "method": "url",
        },
    )
    monkeypatch.setattr(
        "backend.main.get_active_job_postings",
        lambda url: calls.append(url) or {"count": 3},
    )

    response = client.post(
        "/analyze",
        json={"text": "Apply here: https://example.com/careers"},
    )

    assert response.status_code == 200
    assert calls == []
