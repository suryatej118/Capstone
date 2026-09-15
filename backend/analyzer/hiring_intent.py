"""
Deterministic Hiring Intent scoring.

This module is intentionally pure:
- No network calls
- No database access
- No scraping

The enrichment layer is responsible for collecting evidence and passing
it through the signals dictionary.
"""

from typing import Dict, Any, Tuple, List, Optional
import re


# ---------------------------------------------------------------------------
# Authoritative positive weights
# Total = 100
# ---------------------------------------------------------------------------

WEIGHTS = {
    "corporate_domain_present": 15,
    "careers_page_present": 20,
    "recruiter_email_corporate": 20,
    "opencorporates_match": 15,
    "active_job_postings_count": 10,
    "github_org_activity": 7,
    "domain_age": 5,
    "search_presence_hiring": 8,
}

NEGATIVE_PENALTY = 20
MAX_POSITIVE = sum(WEIGHTS.values())


FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "yandex.com",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _domain_from_email(email: Optional[str]) -> Optional[str]:
    """Extract the domain portion from an email address."""
    if not email or "@" not in email:
        return None

    return email.split("@", 1)[1].lower()


def _domain_from_text(text: str) -> Optional[str]:
    """Extract the first domain-looking value from text."""
    if not text:
        return None

    match = re.search(
        r"(?:https?://)?(?:www\.)?([A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        text,
    )

    return match.group(1).lower() if match else None


def _is_free_email(email: Optional[str]) -> bool:
    """Return True if the email uses a known free-email provider."""
    domain = _domain_from_email(email)

    if not domain:
        return True

    return domain in FREE_EMAIL_DOMAINS


def _score_domain_age(age_years: Optional[float]) -> int:
    """
    Convert domain age into the authoritative 0-5 score.

    >= 5 years       -> 5
    2 to <5 years    -> linear mapping from 0 to 5
    1 to <2 years    -> 1
    <1 year          -> 0
    missing/invalid  -> 0
    """
    if age_years is None:
        return 0

    try:
        age = float(age_years)
    except (TypeError, ValueError):
        return 0

    if age >= 5:
        return 5

    if age >= 2:
        return round(((age - 2) / 3) * 5)

    if age >= 1:
        return 1

    return 0


def _score_active_postings(count: Optional[int]) -> int:
    """
    Convert active job-posting count into the authoritative 0-10 score.

    >=5 -> 10
    1-4 -> proportional score
    0/missing -> 0
    """
    if count is None:
        return 0

    try:
        count = int(count)
    except (TypeError, ValueError):
        return 0

    if count <= 0:
        return 0

    if count >= 5:
        return 10

    return round((count / 5) * 10)


def _score_github_activity(
    github_org: Optional[Dict[str, Any]],
    company_domain: Optional[str],
) -> int:
    """
    Calculate the GitHub score.

    +3 organization exists
    +3 recent activity
    +1 organization website matches company domain
    Maximum = 7
    """
    if not github_org:
        return 0

    score = 0

    if github_org.get("exists"):
        score += 3

    if github_org.get("recent_activity"):
        score += 3

    website = github_org.get("website")

    if website and company_domain:
        website_domain = _domain_from_text(str(website))

        if website_domain == company_domain:
            score += 1

    return min(score, WEIGHTS["github_org_activity"])


def _detect_payment_request(text: str) -> bool:
    """
    Detect an explicit monetary payment request.

    This is intentionally conservative and only looks for a payment-related
    request combined with a currency amount.
    """
    if not text:
        return False

    payment_keyword = re.search(
        r"\b(pay|fee|charge|transfer|send money|registration fee|processing fee)\b",
        text,
        re.I,
    )

    if not payment_keyword:
        return False

    currency_amount = (
    re.search(r"[\$\u20B9\u20AC\u00A3]\s*\d{1,}", text)
    or re.search(r"\b(?:Rs\.?|INR|USD|EUR|GBP)\s*\d+\b", text, re.I)
    or re.search(r"\b\d+\s?(?:USD|INR|EUR|GBP)\b", text, re.I)
    )

    return bool(currency_amount)


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def compute_hiring_intent(
    text: str,
    signals: Optional[Dict[str, Any]] = None,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Compute the deterministic Hiring Intent Score.

    Returns:
        (
            hiring_intent_score,
            per_signal_breakdown
        )

    Each signal contains:
        signal
        value
        score
        confidence
    """

    if signals is None:
        signals = {}

    reasons: List[Dict[str, Any]] = []
    positive_score = 0

    # -----------------------------------------------------------------------
    # 1. Corporate domain
    # -----------------------------------------------------------------------

    company_domain = (
        signals.get("company_domain")
        or _domain_from_text(text)
    )

    corporate_domain_present = (
        bool(signals.get("corporate_domain_present"))
        or bool(company_domain)
    )

    corporate_score = (
        WEIGHTS["corporate_domain_present"]
        if corporate_domain_present
        else 0
    )

    reasons.append({
        "signal": "corporate_domain_present",
        "value": corporate_domain_present,
        "score": corporate_score,
        "confidence": 90,
    })

    positive_score += corporate_score

    # -----------------------------------------------------------------------
    # 2. Careers page
    # -----------------------------------------------------------------------

    careers_page_present = bool(
        signals.get("careers_page_present", False)
    )

    careers_score = (
        WEIGHTS["careers_page_present"]
        if careers_page_present
        else 0
    )

    reasons.append({
        "signal": "careers_page_present",
        "value": careers_page_present,
        "score": careers_score,
        "confidence": 80,
    })

    positive_score += careers_score

    # -----------------------------------------------------------------------
    # 3. Recruiter corporate email
    # -----------------------------------------------------------------------

    recruiter_email = signals.get("recruiter_email")

    recruiter_domain = _domain_from_email(recruiter_email)

    recruiter_score = 0
    recruiter_confidence = 40

    if recruiter_email:
        if (
            recruiter_domain
            and company_domain
            and recruiter_domain == company_domain
        ):
            # Exact company-domain match
            recruiter_score = WEIGHTS["recruiter_email_corporate"]
            recruiter_confidence = 95

        elif (
            recruiter_domain
            and recruiter_domain not in FREE_EMAIL_DOMAINS
        ):
            # Corporate-looking domain, but not an exact company match
            recruiter_score = 10
            recruiter_confidence = 80

        elif _is_free_email(recruiter_email):
            recruiter_score = 0
            recruiter_confidence = 90

    reasons.append({
        "signal": "recruiter_email_corporate",
        "value": recruiter_email,
        "score": recruiter_score,
        "confidence": recruiter_confidence,
    })

    positive_score += recruiter_score

    # -----------------------------------------------------------------------
    # 4. OpenCorporates
    # -----------------------------------------------------------------------

    opencorporates_match = signals.get("opencorporates_match")

    if opencorporates_match == "pending":
        oc_score = 0
        oc_confidence = 40

    elif opencorporates_match is True:
        oc_score = WEIGHTS["opencorporates_match"]
        oc_confidence = 80

    else:
        oc_score = 0
        oc_confidence = 60

    reasons.append({
        "signal": "opencorporates_match",
        "value": opencorporates_match,
        "score": oc_score,
        "confidence": oc_confidence,
    })

    positive_score += oc_score

    # -----------------------------------------------------------------------
    # 5. Active job postings
    # -----------------------------------------------------------------------

    active_job_postings_count = signals.get(
        "active_job_postings_count"
    )

    postings_score = _score_active_postings(
        active_job_postings_count
    )

    reasons.append({
        "signal": "active_job_postings_count",
        "value": active_job_postings_count,
        "score": postings_score,
        "confidence": 60,
    })

    positive_score += postings_score

    # -----------------------------------------------------------------------
    # 6. GitHub activity
    # -----------------------------------------------------------------------

    github_org = signals.get("github_org")

    github_score = _score_github_activity(
        github_org,
        company_domain,
    )

    reasons.append({
        "signal": "github_org_activity",
        "value": github_org,
        "score": github_score,
        "confidence": 70,
    })

    positive_score += github_score

    # -----------------------------------------------------------------------
    # 7. Domain age
    # -----------------------------------------------------------------------

    domain_age_years = signals.get("domain_age_years")

    domain_age_score = _score_domain_age(
        domain_age_years
    )

    reasons.append({
        "signal": "domain_age_years",
        "value": domain_age_years,
        "score": domain_age_score,
        "confidence": 60,
    })

    positive_score += domain_age_score

    # -----------------------------------------------------------------------
    # 8. Search presence
    # -----------------------------------------------------------------------

    search_presence = signals.get(
        "search_presence_hiring"
    )

    if search_presence is None:
        search_score = 0

    else:
        try:
            search_score = min(
                WEIGHTS["search_presence_hiring"],
                max(0, int(search_presence)),
            )
        except (TypeError, ValueError):
            search_score = 0

    reasons.append({
        "signal": "search_presence_hiring",
        "value": search_presence,
        "score": search_score,
        "confidence": 50,
    })

    positive_score += search_score

    # -----------------------------------------------------------------------
    # Negative penalty
    # -----------------------------------------------------------------------

    negative_detected = False
    negative_reasons: List[str] = []

    explicit_negative_reason = signals.get("negative_reason")

    if explicit_negative_reason:
        negative_detected = True
        negative_reasons.append(
            str(explicit_negative_reason)
        )

    elif _detect_payment_request(text):
        negative_detected = True
        negative_reasons.append(
            "payment_request_detected_in_text"
        )

    negative_total = (
        NEGATIVE_PENALTY
        if negative_detected
        else 0
    )

    reasons.append({
        "signal": "negative_penalty",
        "value": negative_reasons or None,
        "score": -negative_total,
        "confidence": 95 if negative_detected else 0,
    })

    # -----------------------------------------------------------------------
    # Final score
    # -----------------------------------------------------------------------

    positive_score = min(
        positive_score,
        MAX_POSITIVE,
    )

    raw_score = positive_score - negative_total

    final_score = max(
        0,
        min(100, round(raw_score)),
    )

    return final_score, reasons