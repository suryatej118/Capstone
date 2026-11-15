from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.types import JSON

from backend.database import Base


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)

    requester_id = Column(String(255), nullable=True, index=True)
    platform = Column(String(100), nullable=True)

    # Original submitted job message.
    submitted_text = Column(Text, nullable=False)

    # Detection scores and classification.
    rule_score = Column(Integer, nullable=False)
    ml_probability = Column(Float, nullable=True)
    final_score = Column(Float, nullable=False)
    risk_level = Column(String(30), nullable=False, index=True)
    confidence = Column(Integer, nullable=False)

    # Hiring-intent analysis.
    hiring_intent_score = Column(Integer, nullable=False)

    # Preserve the complete analysis evidence.
    reasons = Column(JSON, nullable=False, default=list)
    highlighted_spans = Column(JSON, nullable=False, default=list)
    hiring_intent_reasons = Column(JSON, nullable=False, default=list)
    suggested_templates = Column(JSON, nullable=False, default=list)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )