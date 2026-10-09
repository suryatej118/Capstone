from pathlib import Path

import joblib


MODEL_PATH = Path("data/scam_model.joblib")

_model = None


def get_model():
    """
    Load the trained model once and reuse it.

    This avoids loading the .joblib file for every API request.
    """
    global _model

    if _model is None:
        _model = joblib.load(MODEL_PATH)

    return _model


def predict_scam_probability(text: str) -> float:
    """
    Return the model's probability that the text is a scam.
    """
    model = get_model()

    probability = model.predict_proba([text])[0][1]

    return float(probability)


if __name__ == "__main__":
    test_text = (
        "Congratulations! Pay Rs. 2000 registration fee today. "
        "Apply now!"
    )

    probability = predict_scam_probability(test_text)

    print(f"Scam probability: {probability:.4f}")