
from backend.analyzer.rules import analyze_rules


def triggered_ids(text):
    _, triggered = analyze_rules(text)
    return {rule.rule_id for rule in triggered}


def test_detects_interview_fee_without_currency_amount():
    ids = triggered_ids(
        "Pay a fee to access the hiring manager's private interview calendar."
    )
    assert "R01" in ids


def test_detects_equipment_deposit_without_currency_amount():
    ids = triggered_ids(
        "Pay a deposit to ship company equipment before receiving an offer."
    )
    assert "R01" in ids


def test_detects_gift_card_payment_request():
    ids = triggered_ids(
        "Buy gift cards and send the redemption codes to confirm your selection."
    )
    assert "R01" in ids


def test_detects_explicit_otp_request():
    ids = triggered_ids(
        "Send your OTP to the recruiter to activate your salary account."
    )
    assert "R02" in ids


def test_legitimate_interview_invitation_does_not_trigger_fee_rule():
    ids = triggered_ids(
        "The recruiter invites you to a free interview and asks for your availability."
    )
    assert "R01" not in ids


def test_legitimate_salary_discussion_does_not_trigger_fee_rule():
    ids = triggered_ids(
        "The recruiter explains the salary range and asks about your expectations."
    )
    assert "R01" not in ids


def test_rule_score_stays_within_zero_to_100():
    score, _ = analyze_rules(
        "Pay a registration fee of Rs 2000 today. "
        "Send your OTP to this personal account urgently."
    )
    assert 0 <= score <= 100


def test_otp_safety_warning_does_not_trigger_sensitive_data_rule():
    _, triggered = analyze_rules(
        "Never share your OTP with anyone claiming to be a recruiter."
    )
    assert "R02" not in {rule.rule_id for rule in triggered}


def test_banking_warning_does_not_trigger_sensitive_data_rule():
    _, triggered = analyze_rules(
        "Never share your banking password or OTP with anyone."
    )
    assert "R02" not in {rule.rule_id for rule in triggered}


def test_direct_otp_request_still_triggers_sensitive_data_rule():
    _, triggered = analyze_rules(
        "Send your OTP to the recruiter to activate your salary account."
    )
    assert "R02" in {rule.rule_id for rule in triggered}
