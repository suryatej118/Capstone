"""Evaluate Job Scam Radar's text classifier on ScamShield's job-only test split.

This script trains a fresh TF-IDF + Logistic Regression model in memory using
data/development_dataset_v4.csv, then evaluates it on the independent job rows
from data/scamshield_test.csv. It does NOT load or overwrite the saved model.

Expected test CSV columns: text,label,source
Labels: 0 = safe/legitimate, 1 = scam
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAIN = PROJECT_ROOT / "data" / "development_dataset_v4.csv"
DEFAULT_TEST = PROJECT_ROOT / "data" / "scamshield_test.csv"
DEFAULT_HELDOUT = PROJECT_ROOT / "data" / "heldout_test_dataset.csv"


def normalize_text(value: object) -> str:
    """Normalize text for duplicate/overlap checks without changing model input."""
    text = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", " ", text).strip().casefold()


def load_train(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Training dataset not found: {path}")
    frame = pd.read_csv(path)
    required = {"text", "label"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Training CSV must contain columns: {sorted(required)}")
    frame = frame[["text", "label"]].copy()
    frame["text"] = frame["text"].fillna("").astype(str).str.strip()
    if (frame["text"] == "").any():
        raise ValueError("Training dataset contains blank text.")
    frame["label"] = pd.to_numeric(frame["label"], errors="raise").astype(int)
    if not set(frame["label"].unique()).issubset({0, 1}):
        raise ValueError("Training labels must be 0 (safe) or 1 (scam).")
    if set(frame["label"].unique()) != {0, 1}:
        raise ValueError("Training dataset must contain both labels 0 and 1.")
    frame["_normalized"] = frame["text"].map(normalize_text)
    if frame["_normalized"].duplicated().any():
        duplicates = int(frame["_normalized"].duplicated().sum())
        raise ValueError(
            f"Training dataset contains {duplicates} duplicate normalized texts. "
            "Resolve duplicates before evaluation."
        )
    return frame


def load_test(path: Path) -> tuple[pd.DataFrame, int, int, int]:
    if not path.exists():
        raise FileNotFoundError(
            f"Test dataset not found: {path}\n"
            "Copy the uploaded/downloaded Hugging Face test.csv to "
            "data/scamshield_test.csv."
        )
    frame = pd.read_csv(path)
    required = {"text", "label", "source"}
    if not required.issubset(frame.columns):
        raise ValueError(
            f"Test CSV must contain columns: {sorted(required)}; "
            f"found: {list(frame.columns)}"
        )
    frame = frame[["text", "label", "source"]].copy()
    frame["text"] = frame["text"].fillna("").astype(str).str.strip()
    frame["source"] = frame["source"].fillna("").astype(str).str.strip().str.lower()
    if (frame["text"] == "").any():
        raise ValueError("Test dataset contains blank text.")
    frame["label"] = pd.to_numeric(frame["label"], errors="raise").astype(int)
    if not set(frame["label"].unique()).issubset({0, 1}):
        raise ValueError("Test labels must be 0 (safe) or 1 (scam).")

    unknown_sources = sorted(set(frame["source"]) - {"job", "sms"})
    if unknown_sources:
        print(f"WARNING: Unexpected source values found: {unknown_sources}")

    all_rows = len(frame)
    frame = frame[frame["source"] == "job"].copy()
    if frame.empty:
        raise ValueError("No rows with source='job' found in the test CSV.")

    frame["_normalized"] = frame["text"].map(normalize_text)
    # Duplicate texts with conflicting labels would make evaluation ambiguous.
    conflicts = [
        text for text, group in frame.groupby("_normalized")
        if group["label"].nunique() > 1
    ]
    if conflicts:
        raise ValueError(
            f"Found {len(conflicts)} duplicated job text(s) with conflicting labels. "
            "Resolve them before evaluation."
        )

    before_dedup = len(frame)
    frame = frame.drop_duplicates(subset="_normalized", keep="first").copy()
    removed_duplicates = before_dedup - len(frame)

    if set(frame["label"].unique()) != {0, 1}:
        raise ValueError(
            "The job-only test set must contain both labels 0 and 1 after deduplication."
        )
    return frame, all_rows, before_dedup, removed_duplicates


def read_normalized_texts(path: Path) -> set[str]:
    if not path.exists():
        return set()
    frame = pd.read_csv(path)
    if "text" not in frame.columns:
        return set()
    return set(frame["text"].fillna("").astype(str).map(normalize_text))


def build_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the text classifier on ScamShield job-only test data."
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--test", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--heldout", type=Path, default=DEFAULT_HELDOUT)
    parser.add_argument("--threshold", type=float, default=0.50)
    args = parser.parse_args()

    if not 0.0 <= args.threshold <= 1.0:
        print("ERROR: --threshold must be between 0 and 1.", file=sys.stderr)
        return 2

    try:
        train = load_train(args.train)
        test, all_test_rows, job_rows_before_dedup, duplicates_removed = load_test(args.test)
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    train_texts = set(train["_normalized"])
    test_texts = set(test["_normalized"])
    overlap_train = train_texts & test_texts
    overlap_heldout = read_normalized_texts(args.heldout) & test_texts

    print("=" * 72)
    print("SCAMSHIELD JOB-ONLY TEST EVALUATION")
    print("=" * 72)
    print(f"Training file: {args.train}")
    print(f"Test file:     {args.test}")
    print(f"Rows in supplied test CSV (all sources): {all_test_rows}")
    print(f"Job rows before duplicate removal:       {job_rows_before_dedup}")
    print(f"Duplicate job rows removed:              {duplicates_removed}")
    print(f"Unique job rows used:                    {len(test)}")
    print(f"Training rows:                           {len(train)}")
    print(f"Training label counts:                   {train['label'].value_counts().sort_index().to_dict()}")
    print(f"Test label counts (0=safe, 1=scam):      {test['label'].value_counts().sort_index().to_dict()}")
    print(f"Threshold:                               {args.threshold:.2f}")
    print(f"Exact normalized overlap with training:  {len(overlap_train)}")
    print(f"Exact normalized overlap with synthetic held-out set: {len(overlap_heldout)}")

    if overlap_train:
        print("ERROR: Test data overlaps with training data. Evaluation stopped.", file=sys.stderr)
        return 2
    if overlap_heldout:
        print(
            "WARNING: Some rows overlap with the synthetic held-out set. "
            "This does not overlap with training, but note it in your report."
        )

    print(
        "\nNOTE: This evaluates a fresh TF-IDF + Logistic Regression text classifier, "
        "not the full Job Scam Radar hybrid API/rule/enrichment pipeline."
    )
    print(
        "NOTE: The source dataset is imbalanced; do not report accuracy alone. "
        "The dataset's labels and source quality have not been independently verified."
    )

    model = build_model()
    model.fit(train["text"], train["label"])
    probabilities = model.predict_proba(test["text"])[:, 1]
    predictions = (probabilities >= args.threshold).astype(int)
    y_true = test["label"].to_numpy()

    print("\nMETRICS")
    print(f"Accuracy:          {accuracy_score(y_true, predictions):.4f}")
    print(f"Balanced accuracy: {balanced_accuracy_score(y_true, predictions):.4f}")
    print(f"Scam precision:    {precision_score(y_true, predictions, zero_division=0):.4f}")
    print(f"Scam recall:       {recall_score(y_true, predictions, zero_division=0):.4f}")
    print(f"Scam F1-score:     {f1_score(y_true, predictions, zero_division=0):.4f}")
    try:
        print(f"ROC-AUC:           {roc_auc_score(y_true, probabilities):.4f}")
    except ValueError:
        print("ROC-AUC:           unavailable (test set needs both classes)")

    print("\nCLASSIFICATION REPORT")
    print(
        classification_report(
            y_true,
            predictions,
            labels=[0, 1],
            target_names=["Safe/legitimate (0)", "Scam (1)"],
            digits=4,
            zero_division=0,
        )
    )
    print("CONFUSION MATRIX (rows=actual [0,1], columns=predicted [0,1])")
    print(confusion_matrix(y_true, predictions, labels=[0, 1]))

    error_positions = [i for i, (actual, predicted) in enumerate(zip(y_true, predictions)) if actual != predicted]
    print(f"\nMISCLASSIFIED EXAMPLES: {len(error_positions)}")
    if not error_positions:
        print("No misclassifications at this threshold.")
    for position in error_positions[:20]:
        row = test.iloc[position]
        print("-" * 72)
        print(f"Actual label: {int(row['label'])}; predicted: {int(predictions[position])}")
        print(f"Scam probability: {probabilities[position]:.4f}")
        print(f"Text: {row['text'][:900]}")
    if len(error_positions) > 20:
        print(f"\nOnly the first 20 of {len(error_positions)} errors are shown.")

    print("\nEvaluation complete. No saved model or source CSV was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
