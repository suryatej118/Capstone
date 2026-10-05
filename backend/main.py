from typing import Optional
import re
from backend.analyzer.hiring_intent import compute_hiring_intent
from backend.analyzer.scoring import calculate_final_score, get_risk_level
from backend.ml.predict import predict_scam_probability
from backend.enrichment.domain import extract_emails, extract_domains
from backend.enrichment.company import extract_company_name
from backend.enrichment.careers import detect_careers_page
from backend.enrichment.job_postings import get_active_job_postings
from backend.enrichment.opencorporates import match_company_name
from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.analyzer.rules import analyze_rules


app = FastAPI(
    title="Job Scam Radar API",
    version="0.1.0",
)


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="The job/internship message or post body to analyze")
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


@app.get("/health")
def health_check():
    return {"status": "ok"}



@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    # 1. Run the rule engine
    rule_score, triggered_rules = analyze_rules(request.text)

    # 2. Run the ML model
    ml_probability = predict_scam_probability(request.text)

    # 3. Combine rule + ML scores
    final_score = calculate_final_score(
        rule_score,
        ml_probability,
    )

    # 4. Convert final score into risk level
    risk_level = get_risk_level(final_score)


    # 5. Build API reasons
    reasons = [
        Reason(
            rule_id=rule.rule_id,
            description=rule.description,
            span=rule.span,
            weight=rule.weight,
        )
        for rule in triggered_rules
    ]

    # 6. Build highlighted spans
    highlighted_spans = [
        HighlightedSpan(
            start=rule.start,
            end=rule.end,
            text=rule.span,
        )
        for rule in triggered_rules
        if rule.start >= 0 and rule.end >= 0
    ]

    # 7. Build a minimal signals dictionary for Hiring Intent.
    # Full enrichment will populate additional signals in production.
    signals = {}

    emails = extract_emails(request.text)
    domains = extract_domains(request.text)
    company_name = extract_company_name(request.text)

    careers_result = detect_careers_page(
        request.text,
        domains[0] if domains else None,
    )

    signals["careers_page_present"] = careers_result["present"]

    job_postings_result = get_active_job_postings(
        careers_result["url"],
    )

    signals["active_job_postings_count"] = job_postings_result["count"]

    if emails:
        signals["recruiter_email"] = emails[0]

    if domains:
        signals["company_domain"] = domains[0]

    if company_name:
        signals["company_name"] = company_name

        try:
            oc_result = match_company_name(company_name)

            signals["opencorporates_match"] = oc_result["matched"]

        except Exception:
            # OpenCorporates is an external service.
            # Its failure should not make the entire analysis fail.
            signals["opencorporates_match"] = "pending"
    else:
        signals["opencorporates_match"] = "pending"

    hiring_score, hiring_reasons = compute_hiring_intent(
        request.text,
        signals,
    )

    return AnalyzeResponse(
        rule_score=rule_score,
        ml_probability=ml_probability,
        final_score=final_score,
        risk_level=risk_level,
        confidence=0,
        reasons=reasons,
        highlighted_spans=highlighted_spans,
        hiring_intent_score=hiring_score,
        hiring_intent_reasons=hiring_reasons,
        suggested_templates=[],
    )