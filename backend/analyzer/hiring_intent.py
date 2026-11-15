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
    "rediffmail.com"
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
        normalized_company_domain = _domain_from_text(
            str(company_domain)
        )

        if (
            website_domain
            and normalized_company_domain
            and (
                website_domain == normalized_company_domain
                or website_domain.endswith(
                    "." + normalized_company_domain
                )
            )
        ):
            score += 1

    return min(score, WEIGHTS["github_org_activity"])





def _detect_payment_request(text: str) -> bool:
    """
    Detect an explicit recruitment-related payment demand.
    Ignore clauses that explicitly deny payment requirements.
    """
    if not text:
        return False

    currency = (
        r"(?:₹\s*|Rs\.?\s*|INR\s+|USD\s+|EUR\s+|GBP\s+)"
        r"\d[\d,]*(?:\.\d{1,2})?"
    )

    payment_patterns = [
        # Explicit payment instruction followed by an amount.
        rf"\b(?:pay|transfer|send|deposit|remit)\b"
        rf".{{0,120}}{currency}",

        # Recruitment-related fee, allowing intervening words.
        rf"\b(?:registration|processing|onboarding|"
        rf"verification|interview|training|security|"
        rf"application|joining)\b"
        rf".{{0,80}}\bfee\b"
        rf".{{0,60}}{currency}",

        # Amount followed by a recruitment-related fee.
        rf"{currency}.{{0,60}}"
        rf"\b(?:registration|processing|onboarding|"
        rf"verification|interview|training|security|"
        rf"application|joining)\b"
        rf".{{0,40}}\b(?:fee|charge)\b",
    ]

    # Split at sentence boundaries without splitting "Rs. 2,499".
    clauses = re.split(
        r"(?<=[!?;])\s+|(?<=[.!?])\s+(?=[A-Z])|\n+",
        text,
    )

    for clause in clauses:
        clause = clause.strip()

        if not clause:
            continue

        negated = re.search(
            r"\b(?:no|not|never|without|isn't|is\s+not|"
            r"doesn't|does\s+not|won't|will\s+not)\b"
            r".{0,80}\b(?:fee|payment|pay|charge|deposit)\b",
            clause,
            re.IGNORECASE,
        )

        if negated:
            continue

        if any(
            re.search(pattern, clause, re.IGNORECASE)
            for pattern in payment_patterns
        ):
            return True

    return False



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

    company_domain = signals.get("company_domain")
    company_domain_verified = (
        signals.get("company_domain_verified") is True
    )

    corporate_domain_present = (
        company_domain_verified
        and bool(company_domain)
    )

    corporate_score = (
        WEIGHTS["corporate_domain_present"]
        if corporate_domain_present
        else 0
    )

    reasons.append({
        "signal": "corporate_domain_present",
        "value": company_domain_verified,
        "score": corporate_score,
        "confidence": 90 if company_domain_verified else 30,
    })

    positive_score += corporate_score

    # -----------------------------------------------------------------------
    # 2. Careers page
    # -----------------------------------------------------------------------

    careers_page_verified = (
        signals.get("careers_page_verified") is True
        and company_domain_verified
    )

    careers_score = (
        WEIGHTS["careers_page_present"]
        if careers_page_verified
        else 0
    )

    reasons.append({
        "signal": "careers_page_present",
        "value": careers_page_verified,
        "score": careers_score,
        "confidence": 80 if careers_page_verified else 30,
    })

    positive_score += careers_score

    # -----------------------------------------------------------------------
    # 3. Recruiter corporate email
    # -----------------------------------------------------------------------

    recruiter_email = signals.get("recruiter_email")
    recruiter_domain = _domain_from_email(recruiter_email)

    recruiter_score = 0
    recruiter_confidence = 30

    if recruiter_email:
        if (
            company_domain_verified
            and recruiter_domain
            and recruiter_domain == company_domain.lower().strip()
        ):
            recruiter_score = WEIGHTS["recruiter_email_corporate"]
            recruiter_confidence = 95
        elif _is_free_email(recruiter_email):
            recruiter_confidence = 90
        else:
            # A non-free email domain is not automatically a company domain.
            recruiter_confidence = 40

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

    # A registry name match establishes neither recruiter identity
    # nor authorization to advertise a job.
    oc_score = 0

    if opencorporates_match is True:
        oc_confidence = 80
    elif opencorporates_match is False:
        oc_confidence = 65
    else:
        # Pending or unavailable lookup: evidence is unknown.
        oc_score = 0
        oc_confidence = 40

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

    postings_score = (
        _score_active_postings(active_job_postings_count)
        if careers_page_verified
        else 0
    )

    postings_value_known = active_job_postings_count is not None
    try:
        postings_value_known = (
            postings_value_known and int(active_job_postings_count) >= 0
        )
    except (TypeError, ValueError):
        postings_value_known = False

    reasons.append({
        "signal": "active_job_postings_count",
        "value": active_job_postings_count,
        "score": postings_score,
        # A confirmed zero is different from a failed/unavailable lookup.
        "confidence": 75 if postings_value_known else 30,
    })

    positive_score += postings_score

    # -----------------------------------------------------------------------
    # 6. GitHub activity
    # -----------------------------------------------------------------------

    github_org = signals.get("github_org")

    github_org_verified = (
    signals.get("github_org_verified") is True
    and company_domain_verified
    )

    github_score = (
        _score_github_activity(github_org, company_domain)
        if github_org_verified
        else 0
    )

    github_evidence_known = (
        isinstance(github_org, dict)
        and isinstance(github_org.get("exists"), bool)
    )
    reasons.append({
        "signal": "github_org_activity",
        "value": github_org,
        "score": github_score,
        # Missing lookup result is unknown; an explicit exists=False is known.
        "confidence": (
            75 if github_evidence_known and github_org.get("exists")
            else 60 if github_evidence_known
            else 30
        ),
    })

    positive_score += github_score

    # -----------------------------------------------------------------------
    # 7. Domain age
    # -----------------------------------------------------------------------

    domain_age_years = (
        signals.get("domain_age_years")
        if company_domain_verified
        else None
    )

    domain_age_score = (
        _score_domain_age(domain_age_years)
        if company_domain_verified
        else 0
    )

    try:
        domain_age_known = (
            domain_age_years is not None
            and float(domain_age_years) >= 0
        )
    except (TypeError, ValueError):
        domain_age_known = False

    reasons.append({
        "signal": "domain_age_years",
        "value": domain_age_years,
        "score": domain_age_score,
        # Missing/invalid age is unknown, not evidence of a young domain.
        "confidence": 85 if domain_age_known else 30,
    })

    positive_score += domain_age_score

    # -----------------------------------------------------------------------
    # 8. Search presence
    # -----------------------------------------------------------------------

    search_presence = signals.get("search_presence_hiring")

    search_presence_verified = (
        signals.get("search_presence_verified") is True
        and company_domain_verified
    )

    if search_presence_verified and search_presence is not None:
        try:
            search_score = min(
                WEIGHTS["search_presence_hiring"],
                max(0, int(search_presence)),
            )
        except (TypeError, ValueError):
            search_score = 0
    else:
        search_score = 0

    try:
        search_presence_known = (
            search_presence is not None and int(search_presence) >= 0
        )
    except (TypeError, ValueError):
        search_presence_known = False

    reasons.append({
        "signal": "search_presence_hiring",
        "value": search_presence,
        "score": search_score,
        "confidence": 65 if search_presence_known else 30,
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