"""End-to-end interpretation regression tests for Hiring Intent scoring.

These tests exercise the public compute_hiring_intent function and verify that
missing evidence is not treated as a scam penalty, positive evidence adds the
expected points, explicit payment-risk evidence applies the configured penalty,
and scores remain within the documented range.
"""

from backend.analyzer.hiring_intent import (
    MAX_POSITIVE,
    NEGATIVE_PENALTY,
    WEIGHTS,
    compute_hiring_intent,
)


def _reason_for(reasons, signal_name):
    return next(reason for reason in reasons if reason["signal"] == signal_name)


def test_unavailable_enrichment_does_not_add_negative_penalty():
    text = "We are hiring for an engineering role."

    baseline_score, baseline_reasons = compute_hiring_intent(text, {})
    unavailable_score, unavailable_reasons = compute_hiring_intent(
        text,
        {
            "opencorporates_match": "pending",
            "active_job_postings_count": None,
            "github_org": None,
            "domain_age_years": None,
            "search_presence_hiring": None,
        },
    )

    assert unavailable_score == baseline_score == 0
    assert _reason_for(unavailable_reasons, "negative_penalty")["score"] == 0
    assert _reason_for(baseline_reasons, "negative_penalty")["score"] == 0


def test_confirmed_opencorporates_match_adds_expected_points():
    score, reasons = compute_hiring_intent(
        "We are hiring",
        {"opencorporates_match": True},
    )

    oc_reason = _reason_for(reasons, "opencorporates_match")

    assert oc_reason["score"] == WEIGHTS["opencorporates_match"]
    assert score == WEIGHTS["opencorporates_match"]


def test_explicit_payment_request_applies_configured_negative_penalty():
    _, reasons = compute_hiring_intent(
        "Please pay ₹500 as a registration fee to apply.",
        {},
    )

    penalty = _reason_for(reasons, "negative_penalty")

    assert penalty["score"] == -NEGATIVE_PENALTY
    assert penalty["value"] == ["payment_request_detected_in_text"]


def test_explicit_negative_reason_applies_penalty_and_keeps_score_bounded():
    score, reasons = compute_hiring_intent(
        "We are hiring",
        {
            "corporate_domain_present": True,
            "negative_reason": "confirmed_impersonation",
        },
    )

    penalty = _reason_for(reasons, "negative_penalty")

    assert penalty["score"] == -NEGATIVE_PENALTY
    assert penalty["value"] == ["confirmed_impersonation"]
    assert 0 <= score <= 100


def test_all_positive_signals_reach_maximum_without_exceeding_100():
    score, reasons = compute_hiring_intent(
        "We are hiring",
        {
            "company_domain": "example.com",
            "careers_page_present": True,
            "recruiter_email": "recruiter@example.com",
            "opencorporates_match": True,
            "active_job_postings_count": 5,
            "github_org": {
                "exists": True,
                "recent_activity": True,
                "website": "https://example.com",
            },
            "domain_age_years": 5,
            "search_presence_hiring": 8,
        },
    )

    assert score == MAX_POSITIVE == 100
    assert 0 <= score <= 100
    assert sum(
        reason["score"]
        for reason in reasons
        if reason["signal"] != "negative_penalty"
    ) == MAX_POSITIVE


def test_missing_evidence_does_not_reduce_score_with_an_extra_penalty():
    score, reasons = compute_hiring_intent(
        "We are hiring",
        {
            "opencorporates_match": None,
            "active_job_postings_count": None,
            "github_org": None,
            "domain_age_years": None,
            "search_presence_hiring": None,
        },
    )

    assert score == 0
    assert _reason_for(reasons, "negative_penalty")["score"] == 0
    assert 0 <= score <= 100
