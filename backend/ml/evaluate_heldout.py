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
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dataset(path):
    texts, labels = [], []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not {"text", "label"}.issubset(reader.fieldnames):
            raise ValueError(f"{path} must contain 'text' and 'label' columns.")

        for line_number, row in enumerate(reader, start=2):
            text = (row.get("text") or "").strip()
            raw_label = (row.get("label") or "").strip()
            if not text:
                raise ValueError(f"Empty text at {path}, CSV line {line_number}.")
            try:
                label = int(raw_label)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid label at {path}, CSV line {line_number}: {raw_label!r}"
                ) from exc
            if label not in (0, 1):
                raise ValueError(f"Label must be 0 or 1 at {path}, CSV line {line_number}.")
            texts.append(text)
            labels.append(label)

    if not texts:
        raise ValueError(f"Dataset is empty: {path}")
    if set(labels) != {0, 1}:
        raise ValueError(f"Dataset must contain both labels 0 and 1: {path}")
    if len(set(texts)) != len(texts):
        raise ValueError(f"Duplicate texts found in {path}")
    return texts, labels


def build_model():
    return Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2))),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])


def main():
    parser = argparse.ArgumentParser(
        description="Train on development data and evaluate once on a held-out test set."
    )
    parser.add_argument(
        "--train",
        type=Path,
        default=PROJECT_ROOT / "data" / "development_dataset_v4.csv",
        help="Development/training CSV (default: data/development_dataset_v4.csv).",
    )
    parser.add_argument(
        "--test",
        type=Path,
        default=PROJECT_ROOT / "data" / "heldout_test_dataset.csv",
        help="Held-out test CSV (default: data/heldout_test_dataset.csv).",
    )
    parser.add_argument("--threshold", type=float, default=0.50)
    args = parser.parse_args()

    train_path = args.train if args.train.is_absolute() else PROJECT_ROOT / args.train
    test_path = args.test if args.test.is_absolute() else PROJECT_ROOT / args.test

    if not train_path.exists():
        raise FileNotFoundError(f"Training dataset not found: {train_path}")
    if not test_path.exists():
        raise FileNotFoundError(f"Test dataset not found: {test_path}")
    if not 0.0 < args.threshold < 1.0:
        raise ValueError("Threshold must be greater than 0 and less than 1.")

    train_texts, train_labels = load_dataset(train_path)
    test_texts, test_labels = load_dataset(test_path)

    train_text_set = {text.casefold() for text in train_texts}
    overlap = train_text_set.intersection(text.casefold() for text in test_texts)
    if overlap:
        raise ValueError(
            f"Found {len(overlap)} exact text overlap(s) between training and test data. "
            "Remove overlaps before evaluating."
        )

    print("=" * 64)
    print("JOB SCAM RADAR - HELD-OUT TEST EVALUATION")
    print("=" * 64)
    print(f"Training dataset: {train_path}")
    print(f"Training samples: {len(train_texts)}")
    print(f"Training labels: legitimate={train_labels.count(0)}, scam={train_labels.count(1)}")
    print(f"Test dataset: {test_path}")
    print(f"Test samples: {len(test_texts)}")
    print(f"Test labels: legitimate={test_labels.count(0)}, scam={test_labels.count(1)}")
    print(f"Exact text overlap: {len(overlap)}")
    print(f"Threshold: {args.threshold:.2f}")
    print()
    print("IMPORTANT: This script trains a fresh in-memory model on the development data.")
    print("It does NOT load or overwrite data/scam_model.joblib.")
    print("The held-out test examples are not used for training.")

    model = build_model()
    model.fit(train_texts, train_labels)
    probabilities = model.predict_proba(test_texts)[:, 1]
    predictions = (probabilities >= args.threshold).astype(int)

    print("\nMetrics on held-out examples")
    print("-" * 64)
    print(f"Accuracy:  {accuracy_score(test_labels, predictions):.4f}")
    print(f"Precision: {precision_score(test_labels, predictions, zero_division=0):.4f}")
    print(f"Recall:    {recall_score(test_labels, predictions, zero_division=0):.4f}")
    print(f"F1-score:  {f1_score(test_labels, predictions, zero_division=0):.4f}")

    print("\nClassification report")
    print("-" * 64)
    print(classification_report(
        test_labels,
        predictions,
        labels=[0, 1],
        target_names=["Legitimate (0)", "Scam (1)"],
        zero_division=0,
    ))

    matrix = confusion_matrix(test_labels, predictions, labels=[0, 1])
    print("Confusion matrix (rows=actual, columns=predicted)")
    print("                 Predicted legitimate | Predicted scam")
    print(f"Actual legitimate: {matrix[0][0]:>10}           | {matrix[0][1]}")
    print(f"Actual scam:       {matrix[1][0]:>10}           | {matrix[1][1]}")

    print("\nMisclassified held-out examples")
    print("-" * 64)
    errors = [
        (i + 1, text, actual, int(predicted), float(prob))
        for i, (text, actual, predicted, prob) in enumerate(
            zip(test_texts, test_labels, predictions, probabilities)
        )
        if actual != predicted
    ]
    if not errors:
        print("No errors on this test set.")
    else:
        print(f"Total misclassified: {len(errors)}")
        for number, text, actual, predicted, probability in errors:
            error_type = "FALSE POSITIVE" if actual == 0 else "FALSE NEGATIVE"
            print(f"\n{number}. {error_type}")
            print(f"   Actual: {actual} ({'Legitimate' if actual == 0 else 'Scam'})")
            print(f"   Predicted: {predicted} ({'Legitimate' if predicted == 0 else 'Scam'})")
            print(f"   Scam probability: {probability:.4f}")
            print(f"   Text: {text}")

    print("\nEvaluation finished. No model file was saved or overwritten.")
    print(
        "Caution: this test set is newly authored and synthetic. "
        "It is held out from training, but it is not a substitute for testing on "
        "independently collected, representative real-world examples."
    )


if __name__ == "__main__":
    main()
