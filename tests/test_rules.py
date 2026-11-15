
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

def test_r03_does_not_highlight_unrelated_email():
    text = (
        "Send your Aadhaar details and payment screenshot "
        "to HR. Email: example@gmail.com"
    )

    _, triggered = analyze_rules(text)

    r03 = next(
        (rule for rule in triggered if rule.rule_id == "R03"),
        None,
    )

    assert r03 is None


def test_r03_detects_explicit_payment_instruction():
    text = "Please transfer the amount of Rs. 1999 immediately."

    _, triggered = analyze_rules(text)

    r03 = next(
        rule for rule in triggered if rule.rule_id == "R03"
    )

    assert r03.span == "transfer the amount of Rs. 1999"
    assert text[r03.start:r03.end] == r03.span


def test_r03_detects_explicit_upi_id():
    text = "Send the payment to UPI ID: merchant@okaxis"

    _, triggered = analyze_rules(text)

    r03 = next(
        rule for rule in triggered if rule.rule_id == "R03"
    )

    assert r03.span == "UPI ID: merchant@okaxis"
    assert text[r03.start:r03.end] == r03.span


def test_r03_does_not_treat_normal_email_as_upi():
    text = "Contact HR at merchant@gmail.com"

    _, triggered = analyze_rules(text)

    assert not any(
        rule.rule_id == "R03" for rule in triggered
    )


def test_r01_highlights_onboarding_fee_not_salary():
    text = (
        "Salary: Rs. 6-8 LPA depending on skills and interview "
        "performance. Shortlisted candidates must pay a refundable "
        "onboarding and document verification fee of Rs. 2,499 "
        "before receiving their offer letter."
    )

    _, triggered = analyze_rules(text)

    r01 = next(
        (rule for rule in triggered if rule.rule_id == "R01"),
        None
    )

    assert r01 is not None
    assert "2,499" in r01.span
    assert "6-8 LPA" not in r01.span


def test_apply_now_alone_does_not_trigger_r04():
    text = "Interested candidates can apply now."

    _, triggered = analyze_rules(text)

    assert not any(
        rule.rule_id == "R04" for rule in triggered
    )


def test_explicit_urgency_triggers_r04():
    text = "URGENT! Apply within 24 hours or lose your position."

    _, triggered = analyze_rules(text)

    assert any(
        rule.rule_id == "R04" for rule in triggered
    )


def test_r01_does_not_trigger_when_no_registration_fee_is_required():
    text = (
        "There is no registration fee or payment required "
        "at any stage of the recruitment process."
    )

    _, triggered = analyze_rules(text)

    assert not any(
        rule.rule_id == "R01" for rule in triggered
    )


def test_r01_still_detects_fee_after_a_separate_no_fee_statement():
    text = (
        "There is no registration fee. "
        "However, shortlisted candidates must pay an "
        "onboarding fee of Rs. 2,499."
    )

    _, triggered = analyze_rules(text)

    r01 = next(
        (rule for rule in triggered if rule.rule_id == "R01"),
        None
    )

    assert r01 is not None
    assert "2,499" in r01.span
