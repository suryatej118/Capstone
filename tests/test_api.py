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
        lambda text, domain: {
            "present": False,
            "url": None,
            "method": "none",
        },
    )
    monkeypatch.setattr(
        main,
        "get_active_job_postings",
        lambda url: {"count": 0},
    )
    monkeypatch.setattr(main, "extract_github_org", lambda text: None)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_returns_expected_response(monkeypatch):
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "analyze_rules", lambda text: (20, []))
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.5)

    response = client.post(
        "/analyze",
        json={
            "text": "We are hiring software engineering interns.",
            "platform": "LinkedIn",
            "requester_id": "test-user",
            "save_report": False,
        },
    )

    assert response.status_code == 200
    data = response.json()

    expected_fields = {
        "rule_score",
        "ml_probability",
        "final_score",
        "risk_level",
        "confidence",
        "reasons",
        "highlighted_spans",
        "hiring_intent_score",
        "hiring_intent_reasons",
        "suggested_templates",
    }

    assert expected_fields.issubset(data.keys())
    assert data["rule_score"] == 20
    assert data["ml_probability"] == 0.5
    assert data["final_score"] == 38.0
    assert data["risk_level"] == "High"
    assert isinstance(data["reasons"], list)
    assert isinstance(data["highlighted_spans"], list)
    assert isinstance(data["hiring_intent_score"], int)
    assert isinstance(data["hiring_intent_reasons"], list)
    assert isinstance(data["suggested_templates"], list)


def test_analyze_endpoint_works_when_ml_is_unavailable(monkeypatch):
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "analyze_rules", lambda text: (42, []))
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: None)

    response = client.post(
        "/analyze",
        json={"text": "A sample job posting for testing."},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["rule_score"] == 42
    assert data["ml_probability"] is None
    assert data["final_score"] == 42.0
    assert data["risk_level"] == "Medium"


def test_analyze_endpoint_rejects_missing_text():
    response = client.post(
        "/analyze",
        json={"platform": "LinkedIn"},
    )

    assert response.status_code == 422


def test_legitimate_job_posting_does_not_trigger_payment_rule(monkeypatch):
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.1)

    text = (
        "We are hiring software engineering interns. "
        "Apply through our official careers page. "
        "The recruiter will contact shortlisted candidates."
    )

    response = client.post("/analyze", json={"text": text})

    assert response.status_code == 200
    data = response.json()
    payment_rule_ids = {"R01", "R03"}

    assert not payment_rule_ids.intersection(
        reason["rule_id"] for reason in data["reasons"]
    )


def test_interview_fee_triggers_payment_rule(monkeypatch):
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.8)

    text = (
        "Pay a fee to access the hiring manager's "
        "private interview calendar."
    )

    response = client.post("/analyze", json={"text": text})

    assert response.status_code == 200
    data = response.json()
    triggered_ids = {reason["rule_id"] for reason in data["reasons"]}

    assert "R01" in triggered_ids
    assert data["rule_score"] > 0
    assert data["risk_level"] == "High"


def test_otp_request_triggers_sensitive_data_rule(monkeypatch):
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.8)

    text = "Send your OTP to the recruiter to activate your salary account."
    response = client.post("/analyze", json={"text": text})

    assert response.status_code == 200
    data = response.json()
    triggered_ids = {reason["rule_id"] for reason in data["reasons"]}

    assert "R02" in triggered_ids


def test_highlighted_spans_match_original_message(monkeypatch):
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.8)

    text = "Pay a fee of Rs 2000 to secure this job today."
    response = client.post("/analyze", json={"text": text})

    assert response.status_code == 200
    data = response.json()

    assert data["highlighted_spans"]

    for span in data["highlighted_spans"]:
        assert 0 <= span["start"] < span["end"] <= len(text)
        assert text[span["start"]:span["end"]] == span["text"]


def test_final_score_is_unchanged_but_r01_can_override_risk_band(monkeypatch):
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.8)

    text = "Pay a registration fee of Rs 2000 today."
    response = client.post("/analyze", json={"text": text})

    assert response.status_code == 200
    data = response.json()

    expected_score = round(
        (data["rule_score"] * 0.4) + (0.8 * 100 * 0.6),
        2,
    )
    assert data["final_score"] == expected_score

    # The score retains its original numerical band, but R01 is a safeguard.
    triggered_ids = {reason["rule_id"] for reason in data["reasons"]}
    if "R01" in triggered_ids:
        assert data["risk_level"] == "High"
    elif expected_score <= 34:
        assert data["risk_level"] == "Low"
    elif expected_score <= 64:
        assert data["risk_level"] == "Medium"
    else:
        assert data["risk_level"] == "High"


def test_r01_payment_request_gets_high_risk_when_ml_probability_is_low(
    monkeypatch,
):
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
