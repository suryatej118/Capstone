LOW_MAX_SCORE = 34.0
MEDIUM_MAX_SCORE = 64.0


def calculate_final_score(rule_score: int, ml_probability: float | None) -> float:
    """
    Calculate the hybrid scam score.

    Rule score contributes 40%.
    ML probability contributes 60%.

    If the ML model is unavailable, the rule score is returned
    temporarily so the API can still function.
    """

    if ml_probability is None:
        return float(min(100, max(0, rule_score)))

    if isinstance(ml_probability, bool):
        raise TypeError("ML probability must be a number between 0 and 1.")

    try:
        ml_probability = float(ml_probability)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "ML probability must be a number between 0 and 1."
        ) from exc

    if not 0.0 <= ml_probability <= 1.0:
        raise ValueError("ML probability must be between 0 and 1.")

    rule_score = min(100, max(0, rule_score))
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

    try:
        final_score = float(final_score)
    except (TypeError, ValueError) as exc:
        raise TypeError("Final score must be a number from 0 to 100.") from exc

    if final_score != final_score:
        raise ValueError("Final score must be a number from 0 to 100.")

    final_score = min(100.0, max(0.0, final_score))

    if final_score <= LOW_MAX_SCORE:
        return "Low"

    if final_score <= MEDIUM_MAX_SCORE:
        return "Medium"

    return "High"