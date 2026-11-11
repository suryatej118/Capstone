from backend.analyzer.hiring_intent import compute_hiring_intent
from backend.analyzer.hiring_intent import _detect_payment_request

def test_clear_legit_case():
    signals = {
        "company_domain": "acme.com",
        "company_domain_verified": True,
        "corporate_domain_present": True,

        "careers_page_present": True,
        "careers_page_verified": True,

        "recruiter_email": "hr@acme.com",
        "opencorporates_match": True,

        "active_job_postings_count": 6,

        "github_org": {
            "exists": True,
            "recent_activity": True,
            "website": "https://acme.com",
        },
        "github_org_verified": True,

        "domain_age_years": 6,

        "search_presence_hiring": 8,
        "search_presence_verified": True,
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
        "company_domain": "acme.com",
        "company_domain_verified": True,
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
        "company_domain": "acme.com",
        "company_domain_verified": True,
        "careers_page_verified": True,
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


def test_confirmed_opencorporates_match_adds_expected_points():
    score, reasons = compute_hiring_intent(
        "We are hiring",
        {"opencorporates_match": True},
    )

    oc_reason = next(
        reason
        for reason in reasons
        if reason["signal"] == "opencorporates_match"
    )

    assert oc_reason["score"] == 0
    assert oc_reason["confidence"] == 80
    assert score == 0


def test_maximum_score_is_85():
    signals = {
        "company_domain": "acme.com",
        "company_domain_verified": True,
        "corporate_domain_present": True,
        "careers_page_present": True,
        "careers_page_verified": True,
        "recruiter_email": "hr@acme.com",
        "opencorporates_match": True,
        "active_job_postings_count": 6,
        "github_org": {
            "exists": True,
            "recent_activity": True,
            "website": "https://acme.com",
        },
        "github_org_verified": True,
        "domain_age_years": 6,
        "search_presence_hiring": 8,
        "search_presence_verified": True,
    }

    score, reasons = compute_hiring_intent(
        "We are hiring",
        signals,
    )

    assert score == 85


def test_gmail_recruiter_email_does_not_count_as_corporate_domain():
    text = (
        "Global Tech Solutions is hiring. "
        "Contact: globaltech.hr2026@gmail.com"
    )

    score, reasons = compute_hiring_intent(
        text,
        signals={
            "recruiter_email": "globaltech.hr2026@gmail.com",
        },
    )

    signals_by_name = {
        item["signal"]: item for item in reasons
    }

    assert signals_by_name["corporate_domain_present"]["value"] is False
    assert signals_by_name["corporate_domain_present"]["score"] == 0

    assert signals_by_name["recruiter_email_corporate"]["score"] == 0

def test_unverified_signals_do_not_increase_hiring_intent():
    signals = {
        "company_domain": "example.com",
        "corporate_domain_present": True,
        "careers_page_present": True,
        "recruiter_email": "hr@example.com",
        "opencorporates_match": True,
        "active_job_postings_count": 10,
        "github_org": {
            "exists": True,
            "recent_activity": True,
            "website": "https://example.com",
        },
        "domain_age_years": 20,
        "search_presence_hiring": 8,
    }

    score, reasons = compute_hiring_intent(
        "We are hiring",
        signals,
    )

    assert score == 0

    for reason in reasons:
        if reason["signal"] != "negative_penalty":
            assert reason["score"] == 0


def test_unverified_domain_gets_no_corporate_or_age_points():
    score, reasons = compute_hiring_intent(
        "Example Company is hiring.",
        {
            "company_domain": "example.com",
            "company_domain_verified": False,
            "corporate_domain_present": True,
            "domain_age_years": 30,
        },
    )

    signals_by_name = {
        item["signal"]: item for item in reasons
    }

    assert signals_by_name["corporate_domain_present"]["score"] == 0
    assert signals_by_name["domain_age_years"]["score"] == 0


def test_no_payment_required_is_not_penalized():
    text = (
        "There is no registration fee or payment required "
        "at any stage of the recruitment process. "
        "Salary: Rs. 20,000 per month."
    )
    assert _detect_payment_request(text) is False


def test_explicit_registration_fee_is_detected():
    text = (
        "A refundable registration fee of Rs. 1,999 "
        "is required before joining."
    )
    assert _detect_payment_request(text) is True


def test_onboarding_fee_is_detected():
    text = (
        "Shortlisted candidates must pay a refundable "
        "onboarding and document verification fee of Rs. 2,499."
    )
    assert _detect_payment_request(text) is True


def test_salary_alone_is_not_a_payment_request():
    text = (
        "Salary: Rs. 6-8 LPA depending on skills "
        "and interview performance."
    )
    assert _detect_payment_request(text) is False
