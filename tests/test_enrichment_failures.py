
from fastapi.testclient import TestClient

from backend import main


client = TestClient(main.app)


def configure_safe_defaults(monkeypatch):
    """Mock enrichment services except the one under test."""
    monkeypatch.setattr(main, "analyze_rules", lambda text: (0, []))
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.2)

    monkeypatch.setattr(main, "extract_emails", lambda text: [])
    monkeypatch.setattr(main, "extract_domains", lambda text: [])
    monkeypatch.setattr(main, "extract_company_name", lambda text: None)

    monkeypatch.setattr(
        main,
        "detect_careers_page",
        lambda text, domain: {"present": False, "url": None},
    )
    monkeypatch.setattr(
        main,
        "get_active_job_postings",
        lambda url: {"count": 0},
    )
    monkeypatch.setattr(
        main,
        "get_domain_age_years",
        lambda domain: None,
    )
    monkeypatch.setattr(
        main,
        "extract_github_org",
        lambda text: None,
    )
    monkeypatch.setattr(
        main,
        "get_github_activity",
        lambda org, domain: {
            "exists": None,
            "recent_activity": None,
            "website": None,
        },
    )
    monkeypatch.setattr(
        main,
        "match_company_name",
        lambda name: {"matched": "pending"},
    )


def post_sample_message():
    return client.post(
        "/analyze",
        json={
            "text": "We are hiring software engineering interns.",
            "save_report": False,
        },
    )


def test_api_survives_whois_failure(monkeypatch):
    configure_safe_defaults(monkeypatch)

    monkeypatch.setattr(
        main,
        "extract_domains",
        lambda text: ["example.com"],
    )

    def fail_whois(domain):
        raise RuntimeError("Simulated WHOIS outage")

    monkeypatch.setattr(main, "get_domain_age_years", fail_whois)

    response = post_sample_message()

    assert response.status_code == 200
    assert "final_score" in response.json()


def test_api_survives_careers_lookup_failure(monkeypatch):
    configure_safe_defaults(monkeypatch)

    def fail_careers(text, domain):
        raise RuntimeError("Simulated careers lookup outage")

    monkeypatch.setattr(main, "detect_careers_page", fail_careers)

    response = post_sample_message()

    assert response.status_code == 200
    assert "final_score" in response.json()


def test_api_survives_job_postings_failure(monkeypatch):
    configure_safe_defaults(monkeypatch)

    def fail_job_postings(url):
        raise RuntimeError("Simulated job postings outage")

    monkeypatch.setattr(
        main,
        "get_active_job_postings",
        fail_job_postings,
    )

    response = post_sample_message()

    assert response.status_code == 200
    assert "final_score" in response.json()


def test_api_survives_github_failure(monkeypatch):
    configure_safe_defaults(monkeypatch)

    monkeypatch.setattr(
        main,
        "extract_github_org",
        lambda text: "example-org",
    )

    def fail_github(org, domain):
        raise RuntimeError("Simulated GitHub outage")

    monkeypatch.setattr(main, "get_github_activity", fail_github)

    response = post_sample_message()

    assert response.status_code == 200
    assert "final_score" in response.json()


def test_api_survives_opencorporates_failure(monkeypatch):
    configure_safe_defaults(monkeypatch)

    monkeypatch.setattr(
        main,
        "extract_company_name",
        lambda text: "Example Company",
    )

    def fail_opencorporates(name):
        raise RuntimeError("Simulated OpenCorporates outage")

    monkeypatch.setattr(
        main,
        "match_company_name",
        fail_opencorporates,
    )

    response = post_sample_message()

    assert response.status_code == 200
    assert "final_score" in response.json()

    data = response.json()

    opencorporates_signals = [
        item
        for item in data["hiring_intent_reasons"]
        if item["signal"] == "opencorporates_match"
    ]

    assert len(opencorporates_signals) == 1
    assert opencorporates_signals[0]["value"] == "pending"
