import logging
import re
import os
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from backend.enrichment.company_website import evaluate_company_website
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models import Scan
from pydantic import BaseModel, Field

from backend.analyzer.hiring_intent import compute_hiring_intent
from backend.analyzer.rules import analyze_rules
from backend.analyzer.scoring import calculate_final_score, get_risk_level
from backend.enrichment.careers import detect_careers_page
from backend.enrichment.company import extract_company_name
from backend.enrichment.domain import (
    extract_emails,
    extract_url_domains,
)

# Backward-compatible name used by existing tests.
extract_domains = extract_url_domains
from backend.enrichment.domain_age import get_domain_age_years
from backend.enrichment.github_activity import (
    extract_github_org,
    get_github_activity,
)
from backend.enrichment.job_postings import get_active_job_postings
from backend.enrichment.opencorporates import match_company_name
from backend.ml.predict import predict_scam_probability

from fastapi.responses import FileResponse
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Job Scam Radar API",
    version="0.1.0",
)
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_URL", "").split(",")
    if origin.strip()
]

if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
Base.metadata.create_all(bind=engine)

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
    scan_id: Optional[int] = None
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
    company_website: dict


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

@app.get("/", include_in_schema=False)
def home():
    frontend_file = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    return FileResponse(frontend_file)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/scans")
def get_scan_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    scans = (
        db.query(Scan)
        .order_by(Scan.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": db.query(Scan).count(),
        "scans": [
            {
                "id": scan.id,
                "platform": scan.platform,
                "risk_level": scan.risk_level,
                "final_score": scan.final_score,
                "confidence": scan.confidence,
                "created_at": (
                    scan.created_at.isoformat()
                    if scan.created_at else None
                ),
                "preview": scan.submitted_text[:150],
            }
            for scan in scans
        ],
    }


@app.get("/scans/{scan_id}")
def get_scan_report(
    scan_id: int,
    db: Session = Depends(get_db),
):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if scan is None:
        raise HTTPException(
            status_code=404,
            detail="Scan report not found",
        )

    return {
        "id": scan.id,
        "requester_id": scan.requester_id,
        "platform": scan.platform,
        "submitted_text": scan.submitted_text,
        "rule_score": scan.rule_score,
        "ml_probability": scan.ml_probability,
        "final_score": scan.final_score,
        "risk_level": scan.risk_level,
        "confidence": scan.confidence,
        "hiring_intent_score": scan.hiring_intent_score,
        "reasons": scan.reasons,
        "highlighted_spans": scan.highlighted_spans,
        "hiring_intent_reasons": scan.hiring_intent_reasons,
        "suggested_templates": scan.suggested_templates,
        "created_at": (
            scan.created_at.isoformat()
            if scan.created_at else None
        ),
    }


@app.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(Scan).count()

    high = db.query(Scan).filter(
        Scan.risk_level == "High"
    ).count()

    medium = db.query(Scan).filter(
        Scan.risk_level == "Medium"
    ).count()

    low = db.query(Scan).filter(
        Scan.risk_level == "Low"
    ).count()

    recent = (
        db.query(Scan)
        .order_by(Scan.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_scans": total,
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low,
        "recent_scans": [
            {
                "id": scan.id,
                "risk_level": scan.risk_level,
                "final_score": scan.final_score,
                "platform": scan.platform,
                "created_at": (
                    scan.created_at.isoformat()
                    if scan.created_at else None
                ),
            }
            for scan in recent
        ],
    }

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
):
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
        logger.exception("URL domain extraction failed")
        domains = []

    try:
        company_name = extract_company_name(request.text)
    except Exception:
        logger.exception("Company-name extraction failed")
        company_name = None

    company_website = evaluate_company_website(company_name) if company_name else {
        "status": "unknown",
        "verified": False,
        "candidate_domain": None,
        "reason": "company_name_not_detected",
    }

    # 6. Domain age lookup.
    # Extracted URLs are unverified. Do not use their domains for company
    # domain-age scoring until ownership has been independently established.

    domain_age_years = None
    signals["domain_age_years"] = None

    signals["company_domain"] = None
    signals["company_domain_verified"] = False

    # 7. Careers-page detection.
    # We can identify a careers-looking URL, but cannot establish that it
    # belongs to the claimed company without verified domain ownership.

    careers_result = {
        "present": False,
        "url": None,
        "method": "none",
    }

    retrieval_checks += 1

    try:
        result = detect_careers_page(request.text, None)

        if isinstance(result, dict):
            careers_result = result
        else:
            logger.warning(
                "Careers lookup returned an unexpected result"
            )
    except Exception:
        logger.exception("Careers-page detection failed")

    careers_url = careers_result.get("url")
    careers_method = careers_result.get("method")

    # Candidate detection is not company verification.
    careers_page_verified = False

    signals["careers_page_present"] = False
    signals["careers_page_verified"] = False
    signals["careers_page_method"] = careers_method
    signals["careers_page_url"] = careers_url

    # 8. Active job postings.
    # Disabled until a careers page is linked to a verified company domain.

    active_job_postings_count = None

    signals["active_job_postings_count"] = None

    # 9. Recruiter email and company information.
    # Extracted email addresses and URLs are retained as raw evidence.
    # Neither establishes company-domain ownership.

    if emails:
        signals["recruiter_email"] = emails[0]

    if company_name:
        signals["company_name"] = company_name

    signals["company_domain"] = None
    signals["company_domain_verified"] = False

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

    # 11. GitHub organization activity.
    # An organization mentioned in a job message is not automatically
    # connected to the claimed company.

    signals["github_org"] = None
    signals["github_org_verified"] = False

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
    response = AnalyzeResponse(
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
        company_website=company_website,
    )

    # Save the completed analysis only when requested.
    if request.save_report:
        scan = Scan(
            requester_id=request.requester_id,
            platform=request.platform,
            submitted_text=request.text,
            rule_score=rule_score,
            ml_probability=ml_probability,
            final_score=final_score,
            risk_level=risk_level,
            confidence=confidence,
            hiring_intent_score=hiring_score,
            reasons=jsonable_encoder(reasons),
            highlighted_spans=jsonable_encoder(highlighted_spans),
            hiring_intent_reasons=jsonable_encoder(hiring_reasons),
            suggested_templates=[],
        )

        try:
            db.add(scan)
            db.commit()
            db.refresh(scan)
            response.scan_id = scan.id
        except Exception:
            db.rollback()
            logger.exception("Failed to save scan report")
            raise HTTPException(
                status_code=500,
                detail="Analysis completed, but saving the report failed.",
            )

    return response
