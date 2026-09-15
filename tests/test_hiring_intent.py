from backend.analyzer.hiring_intent import compute_hiring_intent


def test_clear_legit_case():
    signals = {
        "company_domain": "acme.com",
        "corporate_domain_present": True,
        "careers_page_present": True,
        "recruiter_email": "hr@acme.com",
        "opencorporates_match": True,
        "active_job_postings_count": 6,
        "github_org": {
            "exists": True,
            "recent_activity": True,
            "website": "https://acme.com",
        },
        "domain_age_years": 6,
        "search_presence_hiring": 8,
    }

    score, reasons = compute_hiring_intent(
        "We are hiring",
        signals,
    )

    assert score >= 80


def test_obvious_scam_fee_request():
    text = "Pay a registration fee of 50 USD to apply"

    score, reasons = compute_hiring_intent(
        text,
        {},
    )

    assert score == 0


def test_pending_opencorporates_gives_zero_score():
    signals = {
        "opencorporates_match": "pending",
    }

    score, reasons = compute_hiring_intent(
        "We are hiring",
        signals,
    )

    assert score == 0

    oc_reason = next(
        reason
        for reason in reasons
        if reason["signal"] == "opencorporates_match"
    )

    assert oc_reason["value"] == "pending"
    assert oc_reason["score"] == 0
    assert oc_reason["confidence"] == 40


def test_domain_age_mapping():
    signals = {
        "domain_age_years": 6,
    }

    score, reasons = compute_hiring_intent(
        "We are hiring",
        signals,
    )

    age_reason = next(
        reason
        for reason in reasons
        if reason["signal"] == "domain_age_years"
    )

    assert age_reason["score"] == 5


def test_active_job_posting_mapping():
    signals = {
        "active_job_postings_count": 5,
    }

    score, reasons = compute_hiring_intent(
        "We are hiring",
        signals,
    )

    jobs_reason = next(
        reason
        for reason in reasons
        if reason["signal"] == "active_job_postings_count"
    )

    assert jobs_reason["score"] == 10