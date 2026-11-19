
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
        (rule for rule in triggered if rule.rule_id == "R03"),
        None,
    )

    assert r03 is not None
    assert r03.span == "transfer the amount of Rs. 1999"
    assert text[r03.start:r03.end] == r03.span
    assert not any(rule.rule_id == "R01" for rule in triggered)


def test_upi_destination_only_triggers_r03_not_r01():
    text = "Send the payment to UPI ID: merchant@okaxis"

    _, triggered = analyze_rules(text)
    triggered_ids = {rule.rule_id for rule in triggered}

    assert "R03" in triggered_ids
    assert "R01" not in triggered_ids


def test_personal_account_destination_only_triggers_r03_not_r01():
    text = "Send ₹1,000 to the recruiter's personal account."

    _, triggered = analyze_rules(text)
    triggered_ids = {rule.rule_id for rule in triggered}

    assert "R03" in triggered_ids
    assert "R01" not in triggered_ids


def test_explicit_registration_fee_still_triggers_r01():
    text = "Pay a registration fee of Rs. 2,499."

    _, triggered = analyze_rules(text)
    triggered_ids = {rule.rule_id for rule in triggered}

    assert "R01" in triggered_ids


def test_generic_equipment_deposit_retains_r01_behavior():
    text = "Pay a deposit to ship company equipment before receiving an offer."

    _, triggered = analyze_rules(text)
    triggered_ids = {rule.rule_id for rule in triggered}

    assert "R01" in triggered_ids


def test_recruitment_context_currency_request_without_fee_word():
    text = (
        "You are shortlisted for the role. "
        "Please transfer ₹5,000 to proceed with recruitment."
    )

    _, triggered = analyze_rules(text)
    triggered_ids = {rule.rule_id for rule in triggered}

    # R03 identifies the explicit transfer/destination behavior. R01
    # intentionally does not infer a recruitment fee without fee terminology.
    assert "R03" in triggered_ids
    assert "R01" not in triggered_ids


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


def test_r01_does_not_trigger_for_never_pay_registration_fee_instruction():
    _, triggered = analyze_rules("Never pay a registration fee to apply.")

    assert not any(rule.rule_id == "R01" for rule in triggered)


def test_r01_does_not_trigger_for_do_not_pay_recruiters_instruction():
    _, triggered = analyze_rules("Do not pay money to recruiters.")

    assert not any(rule.rule_id == "R01" for rule in triggered)


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


def test_r01_still_detects_genuine_fee_after_negative_instruction():
    text = (
        "Never pay a registration fee to apply. "
        "However, shortlisted candidates must pay an onboarding fee "
        "of Rs. 2,499."
    )

    _, triggered = analyze_rules(text)
    r01 = next(rule for rule in triggered if rule.rule_id == "R01")

    assert "2,499" in r01.span
    assert text[r01.start:r01.end] == r01.span


def test_r01_newline_negative_instruction_does_not_make_later_transfer_r01():
    text = (
        "Never pay a registration fee\n"
        "Applicants must deposit ₹1,499 to proceed."
    )

    _, triggered = analyze_rules(text)
    triggered_ids = {rule.rule_id for rule in triggered}

    assert "R03" in triggered_ids
    assert "R01" not in triggered_ids


def test_r01_negative_instructions_only_do_not_trigger():
    text = (
        "Never pay a registration fee. "
        "Candidates should not transfer money to recruiters."
    )

    _, triggered = analyze_rules(text)

    assert not any(rule.rule_id == "R01" for rule in triggered)


def test_r01_negative_instruction_ending_at_newline_does_not_trigger():
    text = (
        "Never pay a registration fee\n"
        "For more information, contact HR."
    )

    _, triggered = analyze_rules(text)

    assert not any(rule.rule_id == "R01" for rule in triggered)


def test_r01_newline_negative_instruction_does_not_mask_later_transfer():
    text = (
        "Never pay a registration fee\n"
        "Applicants must deposit ₹1,499 to proceed."
    )

    _, triggered = analyze_rules(text)
    triggered_ids = {rule.rule_id for rule in triggered}

    assert "R03" in triggered_ids
    assert "R01" not in triggered_ids


def test_r01_multiple_newline_negative_instructions_do_not_trigger():
    text = (
        "Never pay a registration fee\n"
        "Do not transfer money to recruiters\n"
        "Candidates should not send deposits"
    )

    _, triggered = analyze_rules(text)

    assert not any(rule.rule_id == "R01" for rule in triggered)


def test_r03_does_not_cross_newlines_for_payment_instruction():
    text = (
        "Never pay a registration fee\n"
        "For more information, contact HR."
    )

    _, triggered = analyze_rules(text)

    assert not any(rule.rule_id == "R03" for rule in triggered)


def test_r02_does_not_trigger_for_otp_safety_statement():
    _, triggered = analyze_rules("Never share your OTP with anyone.")

    assert not any(rule.rule_id == "R02" for rule in triggered)


def test_r02_triggers_bank_request_after_safety_disclaimer():
    text = (
        "Never share your OTP with anyone. "
        "To process payroll, send your bank account number to the recruiter."
    )

    _, triggered = analyze_rules(text)
    r02 = next(rule for rule in triggered if rule.rule_id == "R02")

    assert "send your bank account number" in r02.span
    assert text[r02.start:r02.end] == r02.span


def test_r02_mixed_disclaimer_and_genuine_request():
    text = "Never share your OTP, but send your bank account number to the recruiter."

    _, triggered = analyze_rules(text)
    r02 = next(rule for rule in triggered if rule.rule_id == "R02")

    assert r02.span == "send your bank account number"
    assert text[r02.start:r02.end] == r02.span


def test_r02_mixed_disclaimer_with_however():
    text = "Never share your OTP. However, provide your bank account number to HR."

    _, triggered = analyze_rules(text)
    r02 = next(rule for rule in triggered if rule.rule_id == "R02")

    assert r02.span == "provide your bank account number"
    assert text[r02.start:r02.end] == r02.span


def test_r02_mixed_password_disclaimer_with_but():
    text = "Do not share your password, but send your Aadhaar details to the recruiter."

    _, triggered = analyze_rules(text)
    r02 = next(rule for rule in triggered if rule.rule_id == "R02")

    assert r02.span == "send your Aadhaar"
    assert text[r02.start:r02.end] == r02.span


def test_r02_detects_request_after_same_sentence_disclaimer():
    text = (
        "Never share your OTP, but send your bank account number "
        "to the recruiter."
    )

    _, triggered = analyze_rules(text)
    r02 = next(rule for rule in triggered if rule.rule_id == "R02")

    assert "send your bank account number" in r02.span
    assert text[r02.start:r02.end] == r02.span


def test_r02_disclaimer_for_otp_and_bank_details_does_not_trigger():
    text = "Never share your OTP or bank account details with anyone."

    _, triggered = analyze_rules(text)

    assert not any(rule.rule_id == "R02" for rule in triggered)


def test_r02_preserves_one_match_per_rule_with_multiple_requests():
    text = (
        "Send your bank account number to the recruiter. "
        "Provide your card details as well."
    )

    _, triggered = analyze_rules(text)
    r02_matches = [rule for rule in triggered if rule.rule_id == "R02"]

    assert len(r02_matches) == 1
    assert "Send your bank account number" in r02_matches[0].span
    assert text[r02_matches[0].start:r02_matches[0].end] == r02_matches[0].span


def test_r02_evidence_offsets_preserve_newlines_and_unicode():
    text = (
        "提醒: Never share your OTP.\n"
        "To continue, send your bank account number ₹1,499 to the recruiter."
    )

    _, triggered = analyze_rules(text)
    r02 = next(rule for rule in triggered if rule.rule_id == "R02")

    assert text[r02.start:r02.end] == r02.span
    assert "send your bank account number" in r02.span


def test_r02_triggers_sensitive_request_before_safety_disclaimer():
    text = (
        "Send your bank account number to the recruiter. "
        "Never share your OTP with anyone."
    )

    _, triggered = analyze_rules(text)
    r02 = next(rule for rule in triggered if rule.rule_id == "R02")

    assert "Send your bank account number" in r02.span
    assert text[r02.start:r02.end] == r02.span
