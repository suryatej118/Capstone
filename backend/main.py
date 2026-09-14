from typing import Optional
from backend.analyzer.scoring import calculate_final_score, get_risk_level
from backend.ml.predict import predict_scam_probability
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

    return AnalyzeResponse(
        rule_score=rule_score,
        ml_probability=ml_probability,
        final_score=final_score,
        risk_level=risk_level,
        confidence=0,
        reasons=reasons,
        highlighted_spans=highlighted_spans,
        hiring_intent_score=0,
        hiring_intent_reasons=[],
        suggested_templates=[],
    )