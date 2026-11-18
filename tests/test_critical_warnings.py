import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.analyzer.rules import TriggeredRule, analyze_rules
from backend.analyzer.scoring import get_risk_level
from backend.analyzer.warnings import get_critical_warnings


client = TestClient(main.app)


def triggered(rule_id, description, span):
    return TriggeredRule(
        rule_id=rule_id,
        description=description,
        span=span,
        weight=30,
        start=0,
        end=len(span),
    )


@pytest.mark.parametrize(
    ("final_score", "warning"),
    [
        (34.0, True),
        (34.0, False),
        (64.0, True),
        (64.0, False),
        (100.0, True),
        (100.0, False),
    ],
)
def test_critical_warning_is_independent_of_risk_classification(
    final_score,
    warning,
):
    risk_level = get_risk_level(final_score)
    triggered_rules = (
        [triggered("R01", "Fee/payment request", "pay a ₹1,499 fee")]
        if warning
        else []
    )

    warnings = get_critical_warnings(triggered_rules)

    assert (risk_level in {"Low", "Medium", "High"})
    assert bool(warnings) is warning
    if warning:
        assert warnings[0]["evidence"] == "pay a ₹1,499 fee"


def test_no_critical_warning_for_neutral_rule():
    warnings = get_critical_warnings([
        triggered("R04", "Urgency language", "apply immediately")
    ])

    assert warnings == []


def test_all_high_severity_warning_types_include_exact_evidence():
    warnings = get_critical_warnings([
        triggered("R01", "Fee/payment request", "pay a refundable fee"),
        triggered("R02", "Sensitive data request", "send your Aadhaar"),
        triggered("R03", "Transfer request", "transfer to UPI ID merchant@okaxis"),
    ])

    assert [warning["code"] for warning in warnings] == ["R01", "R02", "R03"]
    assert [warning["evidence"] for warning in warnings] == [
        "pay a refundable fee",
        "send your Aadhaar",
        "transfer to UPI ID merchant@okaxis",
    ]


def mock_enrichment(monkeypatch):
    monkeypatch.setattr(main, "extract_emails", lambda text: [])
    monkeypatch.setattr(main, "extract_domains", lambda text: [])
    monkeypatch.setattr(main, "extract_company_name", lambda text: None)
    monkeypatch.setattr(
        main,
        "detect_careers_page",
        lambda text, domain: {"present": False, "url": None, "method": "none"},
    )


@pytest.mark.parametrize(
    (
        "final_score",
        "ml_probability",
        "rule_score",
        "rule_id",
        "evidence",
        "expected_risk",
    ),
    [
        (12.68, 0.078, 20, "R01", "pay a refundable fee of ₹1,499", "Low"),
        (50.0, 0.5, 50, "R02", "send your bank account number", "Medium"),
        (100.0, 1.0, 100, "R03", "transfer to UPI ID merchant@okaxis", "High"),
        (12.68, 0.078, 20, None, None, "Low"),
        (50.0, 0.5, 50, None, None, "Medium"),
        (100.0, 1.0, 100, None, None, "High"),
    ],
)
def test_requested_risk_and_warning_combinations(
    monkeypatch,
    final_score,
    ml_probability,
    rule_score,
    rule_id,
    evidence,
    expected_risk,
):
    mock_enrichment(monkeypatch)
    monkeypatch.setattr(
        main,
        "predict_scam_probability",
        lambda text: ml_probability,
    )

    def mock_rules(text):
        if rule_id is None:
            return rule_score, []
        return rule_score, [
            triggered(
                rule_id,
                "High-severity indicator",
                evidence,
            )
        ]

    monkeypatch.setattr(main, "analyze_rules", mock_rules)

    text = "A test job posting containing the expected evidence."
    response = client.post(
        "/analyze",
        json={"text": text, "save_report": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == expected_risk
    assert data["final_score"] == final_score

    if rule_id is None:
        assert data["critical_warnings"] == []
    else:
        assert len(data["critical_warnings"]) == 1
        warning = data["critical_warnings"][0]
        assert warning["code"] == rule_id
        assert warning["evidence"] == evidence
        assert evidence in text or evidence in " ".join(
            reason["span"] for reason in data["reasons"]
        )


@pytest.mark.parametrize(
    "text",
    [
        "The policy section discusses payment timelines.",
        "The recruiter explains that bank account details are not required.",
        "The policy discusses payment screenshots and bank account details.",
        "Never transfer money or share your bank account details.",
    ],
)
def test_unrelated_payment_and_bank_words_do_not_create_warnings(text):
    _, triggered_rules = analyze_rules(text)
    warnings = get_critical_warnings(triggered_rules)

    assert warnings == []
    assert not {"R01", "R02", "R03"}.intersection(
        rule.rule_id for rule in triggered_rules
    )


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        (
            "Pay a refundable registration fee of ₹1,499 today.",
            "R01",
        ),
        (
            "Send your bank account number to the recruiter.",
            "R02",
        ),
        (
            "Please transfer Rs. 1999 to confirm the job.",
            "R03",
        ),
    ],
)
def test_real_rules_preserve_exact_matched_evidence(text, rule_id):
    _, triggered_rules = analyze_rules(text)
    rule = next(
        (item for item in triggered_rules if item.rule_id == rule_id),
        None,
    )

    assert rule is not None
    assert rule.span
    assert text[rule.start:rule.end] == rule.span

    warnings = get_critical_warnings([rule])
    assert len(warnings) == 1
    assert warnings[0]["evidence"] == rule.span
