"""Regression tests for unknown versus confirmed Hiring Intent evidence."""

from backend.analyzer.hiring_intent import compute_hiring_intent


def _reason_for(reasons, signal_name):
    return next(reason for reason in reasons if reason["signal"] == signal_name)


def test_missing_domain_age_is_unknown_not_negative_evidence():
    score, reasons = compute_hiring_intent("We are hiring", {})

    domain_age = _reason_for(reasons, "domain_age_years")

    assert score == 0
    assert domain_age["value"] is None
    assert domain_age["score"] == 0
    assert domain_age["confidence"] == 30


def test_unavailable_job_postings_are_distinguished_from_zero():
    _, reasons = compute_hiring_intent(
        "We are hiring",
        {"active_job_postings_count": None},
    )

    postings = _reason_for(reasons, "active_job_postings_count")

    assert postings["value"] is None
    assert postings["score"] == 0
    assert postings["confidence"] == 30


def test_confirmed_zero_job_postings_have_higher_confidence_than_unavailable():
    _, reasons = compute_hiring_intent(
        "We are hiring",
        {"active_job_postings_count": 0},
    )

    postings = _reason_for(reasons, "active_job_postings_count")

    assert postings["value"] == 0
    assert postings["score"] == 0
    assert postings["confidence"] == 75


def test_missing_github_result_is_unknown():
    _, reasons = compute_hiring_intent("We are hiring", {})

    github = _reason_for(reasons, "github_org_activity")

    assert github["value"] is None
    assert github["score"] == 0
    assert github["confidence"] == 30


def test_explicit_github_org_absence_is_distinguished_from_missing_result():
    _, reasons = compute_hiring_intent(
        "We are hiring",
        {"github_org": {"exists": False}},
    )

    github = _reason_for(reasons, "github_org_activity")

    assert github["value"] == {"exists": False}
    assert github["score"] == 0
    assert github["confidence"] == 60
