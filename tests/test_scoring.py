import pytest

from backend.analyzer.scoring import calculate_final_score, get_risk_level


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "Low"),
        (34, "Low"),
        (34.01, "Medium"),
        (64, "Medium"),
        (64.01, "High"),
        (100, "High"),
    ],
)
def test_risk_level_boundaries(score, expected):
    assert get_risk_level(score) == expected


@pytest.mark.parametrize(
    ("rule_score", "ml_probability", "expected"),
    [
        (0, 0.0, 0.0),
        (100, 1.0, 100.0),
        (20, 0.078, 12.68),
        (20, 0.0, 8.0),
        (0, 0.5, 30.0),
        (100, 0.5, 70.0),
        (20, None, 20.0),
    ],
)
def test_hybrid_scoring(rule_score, ml_probability, expected):
    assert calculate_final_score(rule_score, ml_probability) == expected


@pytest.mark.parametrize("ml_probability", [-0.01, 1.01, 7.8, float("nan")])
def test_invalid_ml_probability_is_rejected(ml_probability):
    with pytest.raises(ValueError):
        calculate_final_score(20, ml_probability)


def test_original_production_reproduction():
    final_score = calculate_final_score(20, 0.078)

    assert final_score == 12.68
    assert get_risk_level(final_score) == "Low"
