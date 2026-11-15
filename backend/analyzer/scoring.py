def calculate_final_score(rule_score: int, ml_probability: float | None) -> float:
    """
    Calculate the hybrid scam score.

    Rule score contributes 40%.
    ML probability contributes 60%.

    If the ML model is unavailable, the rule score is returned
    temporarily so the API can still function.
    """

    if ml_probability is None:
        return float(rule_score)

    ml_score = ml_probability * 100

    final_score = (rule_score * 0.4) + (ml_score * 0.6)

    return round(final_score, 2)


def get_risk_level(final_score: float) -> str:
    """
    Convert the final score into the project's risk bands.

    0-34   -> Low
    35-64  -> Medium
    65-100 -> High
    """

    if final_score <= 34:
        return "Low"

    if final_score <= 64:
        return "Medium"

    return "High"