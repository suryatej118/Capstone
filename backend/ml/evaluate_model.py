
import argparse
import csv
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LABEL_NAMES = {0: "Legitimate", 1: "Scam"}
TOP_FEATURES = 15


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate Job Scam Radar using cross-validation."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "data" / "development_dataset_v4.csv",
        help="CSV containing text,label columns.",
    )
    parser.add_argument("--threshold", type=float, default=0.50)
    return parser.parse_args()


def resolve_dataset_path(path):
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_dataset(path):
    texts, labels = [], []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames or not {"text", "label"}.issubset(
            reader.fieldnames
        ):
            raise ValueError("Dataset must contain 'text' and 'label' columns.")

        for line_number, row in enumerate(reader, start=2):
            text = (row.get("text") or "").strip()
            label_value = (row.get("label") or "").strip()

            if not text:
                raise ValueError(f"Empty text at CSV line {line_number}.")

            try:
                label = int(label_value)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid label at CSV line {line_number}: {label_value!r}"
                ) from exc

            if label not in (0, 1):
                raise ValueError(f"Label must be 0 or 1 at CSV line {line_number}.")

            texts.append(text)
            labels.append(label)

    if not texts:
        raise ValueError("The dataset is empty.")

    if set(labels) != {0, 1}:
        raise ValueError("Dataset must contain both labels: 0 and 1.")

    if len(set(texts)) != len(texts):
        print(f"WARNING: {len(texts) - len(set(texts))} duplicate text(s) found.")

    return texts, labels


def build_model():
    return Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2))),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])


def print_feature_inspection(texts, labels):
    model = build_model()
    model.fit(texts, labels)

    vectorizer = model.named_steps["tfidf"]
    coefficients = model.named_steps["classifier"].coef_[0]
    feature_names = vectorizer.get_feature_names_out()

    scam_indices = coefficients.argsort()[::-1][:TOP_FEATURES]
    legitimate_indices = coefficients.argsort()[:TOP_FEATURES]

    print("\nLearned feature inspection")
    print("=" * 60)
    print("Full-dataset fit for inspection only; not independent evaluation.")

    print("\nFeatures most associated with SCAM (label 1)")
    print("-" * 60)
    for i in scam_indices:
        print(f"{feature_names[i]:<30} coefficient: {coefficients[i]:+.4f}")

    print("\nFeatures most associated with LEGITIMATE (label 0)")
    print("-" * 60)
    for i in legitimate_indices:
        print(f"{feature_names[i]:<30} coefficient: {coefficients[i]:+.4f}")


def evaluate(dataset_path, threshold):
    texts, labels = load_dataset(dataset_path)
    counts = {label: labels.count(label) for label in (0, 1)}

    print("=" * 60)
    print("JOB SCAM RADAR - MODEL EVALUATION")
    print("=" * 60)
    print(f"Dataset: {dataset_path}")
    print(f"Total samples: {len(texts)}")
    print(f"Legitimate samples (0): {counts[0]}")
    print(f"Scam samples (1): {counts[1]}")

    if len(texts) < 200:
        print(
            "\nNOTE: This is a small development dataset. "
            "Results are exploratory, not proof of real-world performance."
        )

    folds = min(min(counts.values()), 5)
    if folds < 2:
        raise ValueError("At least two samples per class are required.")

    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)

    # Every example is predicted by a model that did not train on it.
    probabilities = cross_val_predict(
        build_model(),
        texts,
        labels,
        cv=cv,
        method="predict_proba",
    )[:, 1]

    predictions = (probabilities >= threshold).astype(int)

    print(f"\nCross-validation folds: {folds}")
    print(f"Classification threshold: {threshold:.2f}")

    print("\nOverall metrics (out-of-fold predictions)")
    print("-" * 60)
    print(f"Accuracy:  {accuracy_score(labels, predictions):.4f}")
    print(f"Precision: {precision_score(labels, predictions, zero_division=0):.4f}")
    print(f"Recall:    {recall_score(labels, predictions, zero_division=0):.4f}")
    print(f"F1-score:  {f1_score(labels, predictions, zero_division=0):.4f}")

    print("\nClassification report")
    print("-" * 60)
    print(classification_report(
        labels,
        predictions,
        labels=[0, 1],
        target_names=["Legitimate (0)", "Scam (1)"],
        zero_division=0,
    ))

    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    print("\nConfusion matrix")
    print("-" * 60)
    print("Rows = actual labels; columns = predicted labels")
    print("                 Predicted legitimate | Predicted scam")
    print(f"Actual legitimate: {matrix[0][0]:>10}           | {matrix[0][1]}")
    print(f"Actual scam:       {matrix[1][0]:>10}           | {matrix[1][1]}")

    errors = [
        (number, text, actual, int(predicted), float(probability))
        for number, (text, actual, predicted, probability) in enumerate(
            zip(texts, labels, predictions, probabilities), start=1
        )
        if actual != predicted
    ]

    print("\nMisclassified examples with out-of-fold probabilities")
    print("-" * 60)

    if not errors:
        print("No misclassified examples in this evaluation.")
    else:
        print(f"Total misclassified: {len(errors)}")

        for display_number, (
            example_number, text, actual, predicted, probability
        ) in enumerate(errors, start=1):
            distance = abs(probability - threshold)

            print(f"\n{display_number}. Dataset example: {example_number}")
            print(f"   Actual:              {LABEL_NAMES[actual]} ({actual})")
            print(f"   Predicted:           {LABEL_NAMES[predicted]} ({predicted})")
            print(f"   Scam probability:    {probability:.4f}")
            print(f"   Threshold:           {threshold:.2f}")
            print(f"   Distance from:       {distance:.4f}")

            if actual == 0:
                print("   Error type: FALSE POSITIVE")
            else:
                print("   Error type: FALSE NEGATIVE")

            if distance <= 0.05:
                print("   Interpretation: Borderline error")
            elif distance <= 0.20:
                print("   Interpretation: Moderate-confidence error")
            else:
                print("   Interpretation: Stronger model disagreement")

            print(f"   Text: {text}")

    print_feature_inspection(texts, labels)

    print("\nEvaluation complete.")
    print("The saved model file was not loaded or overwritten.")
    print("Cross-validation was used only for evaluation.")


if __name__ == "__main__":
    args = parse_args()
    dataset_path = resolve_dataset_path(args.dataset)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    if not 0.0 < args.threshold < 1.0:
        raise ValueError("Threshold must be greater than 0 and less than 1.")

    evaluate(dataset_path, args.threshold)
