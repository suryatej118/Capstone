"""Evaluate Job Scam Radar's text baseline on independently sourced examples.

This script:
- trains a fresh TF-IDF + Logistic Regression model on the development dataset;
- evaluates on a separately curated real-world dataset;
- requires source and labeling metadata for each evaluation row;
- rejects duplicate texts and exact text overlap with development/held-out datasets;
- does not load, save, or overwrite the production model.

Dataset columns:
text,label,source_url,collected_at,evidence_notes

Labels: 0 = legitimate, 1 = scam.
Only include examples whose labels have been reviewed against documented evidence.
"""

import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse

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
REQUIRED_COLUMNS = {"text", "label", "source_url", "collected_at", "evidence_notes"}


def load_csv(path, require_metadata=False):
    texts, labels, metadata = [], [], []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError(f"{path} is missing a CSV header.")

        required = REQUIRED_COLUMNS if require_metadata else {"text", "label"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"{path} is missing required column(s): {', '.join(sorted(missing))}"
            )

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
                raise ValueError(
                    f"Label must be 0 or 1 at {path}, CSV line {line_number}."
                )

            if require_metadata:
                source_url = (row.get("source_url") or "").strip()
                collected_at = (row.get("collected_at") or "").strip()
                evidence_notes = (row.get("evidence_notes") or "").strip()
                parsed = urlparse(source_url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise ValueError(
                        f"Invalid source_url at {path}, CSV line {line_number}. "
                        "Use a full http(s) URL."
                    )
                if not collected_at:
                    raise ValueError(
                        f"Missing collected_at at {path}, CSV line {line_number}."
                    )
                if not evidence_notes:
                    raise ValueError(
                        f"Missing evidence_notes at {path}, CSV line {line_number}. "
                        "Document why the label is supported."
                    )
                metadata.append({
                    "source_url": source_url,
                    "collected_at": collected_at,
                    "evidence_notes": evidence_notes,
                    "line_number": line_number,
                })

            texts.append(text)
            labels.append(label)

    if not texts:
        raise ValueError(f"Dataset is empty: {path}")
    if set(labels) != {0, 1}:
        raise ValueError(f"Dataset must contain both labels 0 and 1: {path}")

    normalized = [text.casefold() for text in texts]
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"Duplicate texts found in {path}")

    return texts, labels, metadata


def build_model():
    return Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2))),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])


def normalized_texts(path):
    if not path.exists():
        return set()
    texts, _, _ = load_csv(path, require_metadata=False)
    return {text.casefold() for text in texts}


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the text baseline on independently sourced examples. "
            "No model artifact is saved or overwritten."
        )
    )
    parser.add_argument(
        "--train",
        type=Path,
        default=PROJECT_ROOT / "data" / "development_dataset_v4.csv",
        help="Development dataset (default: data/development_dataset_v4.csv).",
    )
    parser.add_argument(
        "--test",
        type=Path,
        default=PROJECT_ROOT / "data" / "real_world_evaluation.csv",
        help="Real-world evaluation CSV (default: data/real_world_evaluation.csv).",
    )
    parser.add_argument(
        "--heldout",
        type=Path,
        default=PROJECT_ROOT / "data" / "heldout_test_dataset.csv",
        help="Optional synthetic held-out dataset used for overlap checks.",
    )
    parser.add_argument("--threshold", type=float, default=0.50)
    args = parser.parse_args()

    train_path = args.train if args.train.is_absolute() else PROJECT_ROOT / args.train
    test_path = args.test if args.test.is_absolute() else PROJECT_ROOT / args.test
    heldout_path = (
        args.heldout if args.heldout.is_absolute() else PROJECT_ROOT / args.heldout
    )

    if not train_path.exists():
        raise FileNotFoundError(f"Training dataset not found: {train_path}")
    if not test_path.exists():
        raise FileNotFoundError(
            f"Real-world evaluation dataset not found: {test_path}\n"
            "Create it from data/real_world_evaluation_template.csv after "
            "collecting and reviewing independent examples."
        )
    if not 0.0 < args.threshold < 1.0:
        raise ValueError("Threshold must be greater than 0 and less than 1.")

    train_texts, train_labels, _ = load_csv(train_path)
    test_texts, test_labels, metadata = load_csv(test_path, require_metadata=True)

    train_set = {text.casefold() for text in train_texts}
    test_set = {text.casefold() for text in test_texts}
    train_overlap = train_set.intersection(test_set)
    if train_overlap:
        raise ValueError(
            f"Found {len(train_overlap)} exact text overlap(s) between training "
            "and real-world evaluation data. Resolve these before evaluation."
        )

    heldout_set = normalized_texts(heldout_path)
    heldout_overlap = heldout_set.intersection(test_set)
    if heldout_overlap:
        raise ValueError(
            f"Found {len(heldout_overlap)} exact text overlap(s) between the "
            "synthetic held-out set and real-world evaluation data."
        )

    print("=" * 72)
    print("JOB SCAM RADAR - REAL-WORLD EVALUATION")
    print("=" * 72)
    print(f"Training dataset: {train_path}")
    print(f"Training samples: {len(train_texts)}")
    print(f"Training labels: legitimate={train_labels.count(0)}, scam={train_labels.count(1)}")
    print(f"Evaluation dataset: {test_path}")
    print(f"Evaluation samples: {len(test_texts)}")
    print(f"Evaluation labels: legitimate={test_labels.count(0)}, scam={test_labels.count(1)}")
    print(f"Exact overlap with training set: {len(train_overlap)}")
    print(f"Exact overlap with synthetic held-out set: {len(heldout_overlap)}")
    print(f"Threshold: {args.threshold:.2f}")
    print()
    print("Labeling metadata checks passed; this script does not independently")
    print("verify source claims or guarantee that human labels are correct.")
    print("A model is trained in memory; no model file is saved or overwritten.")

    model = build_model()
    model.fit(train_texts, train_labels)
    probabilities = model.predict_proba(test_texts)[:, 1]
    predictions = (probabilities >= args.threshold).astype(int)

    print("\nMetrics on real-world evaluation examples")
    print("-" * 72)
    print(f"Accuracy:  {accuracy_score(test_labels, predictions):.4f}")
    print(f"Precision: {precision_score(test_labels, predictions, zero_division=0):.4f}")
    print(f"Recall:    {recall_score(test_labels, predictions, zero_division=0):.4f}")
    print(f"F1-score:  {f1_score(test_labels, predictions, zero_division=0):.4f}")

    print("\nClassification report")
    print("-" * 72)
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

    print("\nMisclassified examples")
    print("-" * 72)
    errors = [
        (i, text, actual, int(predicted), float(probability), metadata[i])
        for i, (text, actual, predicted, probability) in enumerate(
            zip(test_texts, test_labels, predictions, probabilities)
        )
        if actual != predicted
    ]
    if not errors:
        print("No errors on this evaluation set.")
    else:
        print(f"Total misclassified: {len(errors)}")
        for number, text, actual, predicted, probability, row_metadata in errors:
            error_type = "FALSE POSITIVE" if actual == 0 else "FALSE NEGATIVE"
            print(f"\n{number + 1}. {error_type}")
            print(f"   Actual: {'Legitimate' if actual == 0 else 'Scam'} ({actual})")
            print(f"   Predicted: {'Legitimate' if predicted == 0 else 'Scam'} ({predicted})")
            print(f"   Scam probability: {probability:.4f}")
            print(f"   Source: {row_metadata['source_url']}")
            print(f"   Evidence notes: {row_metadata['evidence_notes']}")
            print(f"   Text: {text}")

    print("\nEvaluation finished. No model file was saved or overwritten.")
    print(
        "Interpretation caution: report results with dataset size, source mix, "
        "labeling limitations, and collection period. Do not treat a small or "
        "biased sample as proof of general real-world accuracy."
    )


if __name__ == "__main__":
    main()
