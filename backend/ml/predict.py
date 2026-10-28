
"""Load and use the selected Job Scam Radar text-classification model."""

from pathlib import Path

import joblib


# Resolve paths relative to the project root, not the terminal's directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_MODEL_PATH = (
    PROJECT_ROOT / "data" / "scam_model_scamshield_candidate.joblib"
)
EXISTING_MODEL_PATH = PROJECT_ROOT / "data" / "scam_model.joblib"

_model = None
_loaded_model_path = None


def get_model():
    """Load the candidate model when available; otherwise use the existing model."""
    global _model, _loaded_model_path

    if _model is None:
        if CANDIDATE_MODEL_PATH.exists():
            model_path = CANDIDATE_MODEL_PATH
        elif EXISTING_MODEL_PATH.exists():
            model_path = EXISTING_MODEL_PATH
        else:
            raise FileNotFoundError(
                "No Job Scam Radar model was found. Expected one of:\n"
                f"1. {CANDIDATE_MODEL_PATH}\n"
                f"2. {EXISTING_MODEL_PATH}"
            )

        loaded_model = joblib.load(model_path)

        # Fail early if the saved model cannot return class probabilities.
        if not hasattr(loaded_model, "predict_proba"):
            raise TypeError(
                f"The model at {model_path} does not support predict_proba()."
            )

        if not hasattr(loaded_model, "classes_"):
            raise TypeError(
                f"The model at {model_path} does not expose classes_."
            )

        if 1 not in loaded_model.classes_:
            raise ValueError(
                f"The model at {model_path} has no class 1 (scam). "
                f"Available classes: {loaded_model.classes_}"
            )

        _model = loaded_model
        _loaded_model_path = model_path

        print(f"Job Scam Radar text model loaded: {_loaded_model_path}")

    return _model


def predict_scam_probability(text: str) -> float:
    """
    Return the model's estimated probability for class 1 (scam).

    This function preserves the existing interface used by the application.
    It returns a probability, not a final risk score or classification decision.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    if not text.strip():
        raise ValueError("text must not be empty.")

    model = get_model()

    scam_class_index = list(model.classes_).index(1)
    probability = model.predict_proba([text])[0][scam_class_index]

    return float(probability)


if __name__ == "__main__":
    test_texts = [
        (
            "Congratulations! Pay Rs. 2000 registration fee today. "
            "Apply now!"
        ),
        (
            "Software Engineer internship. Work with our engineering team. "
            "Submit your resume through the official company careers portal."
        ),
    ]

    for test_text in test_texts:
        probability = predict_scam_probability(test_text)
        print(f"\nText: {test_text}")
        print(f"Scam probability: {probability:.4f}")
