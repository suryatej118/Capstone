from fastapi.testclient import TestClient

from backend import main


client = TestClient(main.app)


def mock_enrichment(monkeypatch):
    """Replace external enrichment with predictable local results."""
    monkeypatch.setattr(main, "extract_emails", lambda text: [])
    monkeypatch.setattr(main, "extract_domains", lambda text: [])
    monkeypatch.setattr(main, "extract_company_name", lambda text: None)
    monkeypatch.setattr(
        main,
        "detect_careers_page",
        lambda text, domain: {"present": False, "url": None, "method": "none"},
    )
    monkeypatch.setattr(
        main,
        "get_active_job_postings",
        lambda url: {"count": 0},
    )
    monkeypatch.setattr(main, "extract_github_org", lambda text: None)


def test_r01_payment_request_gets_high_risk_even_when_hybrid_score_is_low(
    monkeypatch,
):
    """R01 must not be downgraded to Low by a low ML probability."""
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(
        main,
        "predict_scam_probability",
        lambda text: 0.11260339987359708,
    )

    text = (
        "Congratulations! You have been selected for a Software Developer "
        "position. Pay a refundable registration fee of Rs. 2,000 today "
        "to confirm your job. Immediate joining."
    )

    response = client.post(
        "/analyze",
        json={
            "text": text,
            "platform": "test",
            "requester_id": "risk-override-test",
            "save_report": False,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["final_score"] < 35
    assert data["risk_level"] == "High"
    assert "R01" in {reason["rule_id"] for reason in data["reasons"]}


def test_non_r01_low_risk_listing_keeps_standard_risk_band(monkeypatch):
    """The targeted override must not change ordinary low-risk cases."""
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "analyze_rules", lambda text: (0, []))
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.1)

    response = client.post(
        "/analyze",
        json={
            "text": "Software engineering internship. Apply through the careers portal.",
            "platform": "test",
            "requester_id": "ordinary-listing-test",
            "save_report": False,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["final_score"] == 6.0
    assert data["risk_level"] == "Medium"
    assert data["reasons"] == []


def test_r01_override_does_not_change_calculated_final_score(monkeypatch):
    """The safeguard changes classification, not the numeric hybrid score."""
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(
        main,
        "predict_scam_probability",
        lambda text: 0.11260339987359708,
    )

    response = client.post(
        "/analyze",
        json={
            "text": "Pay a registration fee today to confirm your job.",
            "platform": "test",
            "requester_id": "score-preservation-test",
            "save_report": False,
        },
    )

    assert response.status_code == 200
    data = response.json()

    expected_score = round(
        (data["rule_score"] * 0.4)
        + (0.11260339987359708 * 100 * 0.6),
        2,
    )
    assert data["final_score"] == expected_score
    assert data["risk_level"] == "High"



def test_safety_warning_about_recruitment_fees_does_not_force_high_risk(
    monkeypatch,
):
    """A warning that tells readers not to pay fees is not itself a demand."""
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.1)

    text = (
        "Never pay a registration fee to get a job. "
        "Legitimate employers do not ask candidates to pay."
    )
    response = client.post(
        "/analyze",
        json={
            "text": text,
            "platform": "test",
            "requester_id": "fee-warning-test",
            "save_report": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "Medium"
