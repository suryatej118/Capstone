import logging
import re
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.analyzer.hiring_intent import compute_hiring_intent
from backend.analyzer.rules import analyze_rules
from backend.analyzer.scoring import calculate_final_score, get_risk_level
from backend.enrichment.careers import detect_careers_page
from backend.enrichment.company import extract_company_name
from backend.enrichment.domain import extract_emails, extract_domains
from backend.enrichment.domain_age import get_domain_age_years
from backend.enrichment.github_activity import (
    extract_github_org,
    get_github_activity,
)
from backend.enrichment.job_postings import get_active_job_postings
from backend.enrichment.opencorporates import match_company_name
from backend.ml.predict import predict_scam_probability


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Job Scam Radar API",
    version="0.1.0",
)


class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        description="The job/internship message or post body to analyze",
    )
    platform: Optional[str] = None
    requester_id: Optional[str] = None
    save_report: bool = True


class Reason(BaseModel):
    rule_id: str
    description: str
    span: str
    weight: float


class HighlightedSpan(BaseModel):
    start: int
    end: int
    text: str


class AnalyzeResponse(BaseModel):
    rule_score: int
    ml_probability: Optional[float] = None
    final_score: float
    risk_level: str
    confidence: int
    reasons: list[Reason]
    highlighted_spans: list[HighlightedSpan]
    hiring_intent_score: int
    hiring_intent_reasons: list[dict]
    suggested_templates: list[dict]


def unknown_github_result():
    """Represent GitHub evidence as unknown when the lookup fails."""
    return {
        "exists": None,
        "recent_activity": None,
        "website": None,
    }


def calculate_confidence(
    triggered_rules: list,
    ml_probability: Optional[float],
    retrieval_strength: float,
) -> int:
    """
    Calculate a heuristic 0-100 confidence indicator.

    Rule certainty: triggered rule weight, normalized against a 30-point
    rule, capped at 100.
    Model certainty: distance from an uncertain probability of 0.5.
    Retrieval strength: 0-100 estimate of how much enrichment evidence
    was successfully available.

    This is a heuristic indicator, not a statistically calibrated
    probability that the result is correct.
    """
    total_rule_weight = sum(
        max(0.0, float(getattr(rule, "weight", 0)))
        for rule in triggered_rules
    )
    rule_certainty = min(100.0, (total_rule_weight / 30.0) * 100.0)

    if ml_probability is None:
        model_certainty = 0.0
    else:
        probability = min(1.0, max(0.0, float(ml_probability)))
        model_certainty = abs(probability - 0.5) * 200.0

    confidence = (
        (rule_certainty * 0.5)
        + (model_certainty * 0.4)
        + (min(100.0, max(0.0, retrieval_strength)) * 0.1)
    )
    return int(round(min(100.0, max(0.0, confidence))))


def apply_high_severity_rule_override(
    calculated_risk_level: str,
    triggered_rules: list,
    text: str,
) -> str:
    """
    Enforce a minimum High classification for R01 payment-demand matches.

    Clear safety warnings/negations are excluded to reduce false positives.
    The numerical hybrid score remains unchanged.
    """
    has_r01 = any(
        getattr(rule, "rule_id", None) == "R01"
        for rule in triggered_rules
    )
    if not has_r01:
        return calculated_risk_level

    safety_warning_patterns = (
        r"\bnever\s+(?:pay|send|transfer|deposit|provide)\b",
        r"\bdo\s+not\s+(?:pay|send|transfer|deposit|provide)\b",
        r"\bdon't\s+(?:pay|send|transfer|deposit|provide)\b",
        r"\bavoid\s+paying\b",
        r"\bno\s+(?:application|registration|recruitment|interview)?\s*"
        r"fee\s+(?:is\s+)?(?:required|necessary|needed)\b",
    )
    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in safety_warning_patterns
    ):
        return calculated_risk_level

    return "High"


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    # 1. Core rule analysis. Core analysis errors are intentionally not hidden.
    rule_score, triggered_rules = analyze_rules(request.text)

    # 2. ML prediction. The predictor may return None if the model is unavailable.
    ml_probability = predict_scam_probability(request.text)

    # 3. Calculate the original hybrid score and its standard risk band.
    # The targeted R01 safeguard changes classification only, not the score.
    
    final_score = calculate_final_score(rule_score, ml_probability)

    # Candidate probability-based risk policy.
    # Preserve the existing score and R01 safeguard.
    if ml_probability is None:
        calculated_risk_level = get_risk_level(final_score)
    elif ml_probability >= 0.20:
        calculated_risk_level = "High"
    elif ml_probability >= 0.10:
        calculated_risk_level = "Medium"
    else:
        calculated_risk_level = "Low"

    risk_level = apply_high_severity_rule_override(
        calculated_risk_level,
        triggered_rules,
        request.text,
    )


    # 4. Build explanations and highlighted spans.
    reasons = [
        Reason(
            rule_id=rule.rule_id,
            description=rule.description,
            span=rule.span,
            weight=rule.weight,
        )
        for rule in triggered_rules
    ]

    highlighted_spans = [
        HighlightedSpan(
            start=rule.start,
            end=rule.end,
            text=rule.span,
        )
        for rule in triggered_rules
        if rule.start >= 0 and rule.end >= 0
    ]

    # 5. Prepare optional enrichment signals. Individual failures must not
    # prevent the core analysis from returning a response.
    signals = {}
    successful_retrievals = 0
    retrieval_checks = 0

    try:
        emails = extract_emails(request.text)
    except Exception:
        logger.exception("Email extraction failed")
        emails = []

    try:
        domains = extract_domains(request.text)
    except Exception:
        logger.exception("Domain extraction failed")
        domains = []

    try:
        company_name = extract_company_name(request.text)
    except Exception:
        logger.exception("Company-name extraction failed")
        company_name = None

    # 6. Domain age lookup.
    domain_age_years = None
    if domains:
        retrieval_checks += 1
        try:
            domain_age_years = get_domain_age_years(domains[0])
            if domain_age_years is not None:
                successful_retrievals += 1
        except Exception:
            logger.exception("Domain-age lookup failed")

    signals["domain_age_years"] = domain_age_years

    # 7. Careers-page detection.
    # A keyword mention or a URL-shaped link is not enough to count as a
    # verified careers page. The current detector uses method="website" only
    # when its website check succeeds.
    careers_result = {"present": False, "url": None, "method": "none"}
    retrieval_checks += 1

    try:
        result = detect_careers_page(
            request.text,
            domains[0] if domains else None,
        )

        if isinstance(result, dict):
            careers_result = result
        else:
            logger.warning("Careers lookup returned an unexpected result")
    except Exception:
        logger.exception("Careers-page lookup failed")

    careers_url = careers_result.get("url")
    careers_method = careers_result.get("method")

    careers_page_verified = (
        careers_result.get("present") is True
        and careers_method == "website"
        and isinstance(careers_url, str)
        and bool(careers_url.strip())
    )

    if careers_page_verified:
        successful_retrievals += 1

    signals["careers_page_present"] = careers_page_verified

    # Preserve the evidence type for diagnostics and future explainability.
    signals["careers_page_method"] = careers_method
    signals["careers_page_url"] = careers_url if careers_page_verified else None

    # 8. Active job postings.
    # Only query a URL that the careers detector verified on the company site.
    # None means unavailable/unknown, not zero active postings.
    active_job_postings_count = None

    if careers_page_verified:
        retrieval_checks += 1
        try:
            job_postings_result = get_active_job_postings(careers_url)

            if isinstance(job_postings_result, dict):
                active_job_postings_count = job_postings_result.get("count")
                if active_job_postings_count is not None:
                    successful_retrievals += 1
            else:
                logger.warning(
                    "Job-postings lookup returned an unexpected result"
                )
        except Exception:
            logger.exception("Active job-postings lookup failed")

    signals["active_job_postings_count"] = active_job_postings_count

    # 9. Recruiter email and company domain.
    if emails:
        signals["recruiter_email"] = emails[0]
    if domains:
        signals["company_domain"] = domains[0]
    if company_name:
        signals["company_name"] = company_name

    # 10. OpenCorporates verification. Failed/unavailable lookups stay pending.
    signals["opencorporates_match"] = "pending"
    if company_name:
        retrieval_checks += 1
        try:
            oc_result = match_company_name(company_name)

            if isinstance(oc_result, dict):
                match_value = oc_result.get("matched", "pending")
                signals["opencorporates_match"] = match_value

                if match_value != "pending" and match_value is not None:
                    successful_retrievals += 1
            else:
                logger.warning("OpenCorporates returned an unexpected result")
        except Exception:
            logger.exception("OpenCorporates lookup failed")

    # 11. GitHub organization activity. Missing/failed evidence is unknown.
    github_org = None
    try:
        github_org = extract_github_org(request.text)
    except Exception:
        logger.exception("GitHub organization extraction failed")

    if github_org:
        retrieval_checks += 1
        try:
            github_result = get_github_activity(
                github_org,
                signals.get("company_domain"),
            )

            if isinstance(github_result, dict):
                signals["github_org"] = github_result
                if github_result.get("exists") is not None:
                    successful_retrievals += 1
            else:
                logger.warning(
                    "GitHub activity lookup returned an unexpected result"
                )
                signals["github_org"] = unknown_github_result()
        except Exception:
            logger.exception("GitHub activity lookup failed")
            signals["github_org"] = unknown_github_result()

    # 12. Confidence: count only usable enrichment evidence as successful.
    retrieval_strength = (
        (successful_retrievals / retrieval_checks) * 100.0
        if retrieval_checks > 0
        else 0.0
    )

    confidence = calculate_confidence(
        triggered_rules=triggered_rules,
        ml_probability=ml_probability,
        retrieval_strength=retrieval_strength,
    )

    # 13. Compute hiring intent from available evidence.
    hiring_score, hiring_reasons = compute_hiring_intent(
        request.text,
        signals,
    )

    # 14. Return the established API response structure.
    return AnalyzeResponse(
        rule_score=rule_score,
        ml_probability=ml_probability,
        final_score=final_score,
        risk_level=risk_level,
        confidence=confidence,
        reasons=reasons,
        highlighted_spans=highlighted_spans,
        hiring_intent_score=hiring_score,
        hiring_intent_reasons=hiring_reasons,
        suggested_templates=[],
    )
