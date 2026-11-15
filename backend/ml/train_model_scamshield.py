"""Train and save a candidate Job Scam Radar text model.

Default behavior is SAFE: it writes to data/scam_model_scamshield_candidate.joblib,
not the existing data/scam_model.joblib.

Uses ScamShield's train.csv rows where source == "job" only. It excludes SMS
and synthetic rows, deduplicates normalized text, and requires both labels.
Run from the repository root:
    python backend/ml/train_model_scamshield.py

Only promote the candidate after evaluating it. To deliberately overwrite the
production model, pass --output data/scam_model.joblib (not recommended until
you have reviewed test results).
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "scamshield_train.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "scam_model_scamshield_candidate.joblib"


def normalize_text(value: object) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", " ", value).strip().casefold()


def load_dataset(dataset_path: Path) -> tuple[list[str], list[int]]:
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {dataset_path}\n"
            "Place the Hugging Face train.csv at data/scamshield_train.csv."
        )

    frame = pd.read_csv(dataset_path)
    required = {"text", "label", "source"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            f"Dataset is missing columns {sorted(missing)}. "
            f"Found columns: {list(frame.columns)}"
        )

    frame = frame[["text", "label", "source"]].copy()
    frame["text"] = frame["text"].fillna("").astype(str).str.strip()
    frame["source"] = frame["source"].fillna("").astype(str).str.strip().str.lower()
    frame["label"] = pd.to_numeric(frame["label"], errors="raise").astype(int)

    if not set(frame["label"].unique()).issubset({0, 1}):
        raise ValueError("Labels must be 0 (safe/legitimate) or 1 (scam).")

    # Exclude SMS and synthetic examples for this job-only baseline.
    frame = frame[(frame["source"] == "job") & (frame["text"] != "")].copy()
    if frame.empty:
        raise ValueError("No non-empty rows with source='job' were found.")

    frame["_normalized"] = frame["text"].map(normalize_text)
    duplicate_count = int(frame["_normalized"].duplicated().sum())
    frame = frame.drop_duplicates(subset="_normalized", keep="first").copy()

    if set(frame["label"].unique()) != {0, 1}:
        raise ValueError(
            "The job-only training data must contain both labels 0 and 1. "
            f"Counts: {frame['label'].value_counts().to_dict()}"
        )

    print(f"Dataset: {dataset_path}")
    print(f"Source rows with source='job' and non-empty text: {len(frame) + duplicate_count}")
    print(f"Duplicate job texts removed: {duplicate_count}")
    print(f"Unique training samples: {len(frame)}")
    print(f"Label counts (0=safe, 1=scam): {frame['label'].value_counts().sort_index().to_dict()}")

    return frame["text"].tolist(), frame["label"].tolist()


def build_model() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                    class_weight=None,
                ),
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    texts, labels = load_dataset(args.dataset)
    model = build_model()
    model.fit(texts, labels)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.output)

    print(f"Candidate model saved to: {args.output}")
    print("The existing data/scam_model.joblib was not changed.")
    print("This script trains the text classifier only, not the rule/enrichment pipeline.")


if __name__ == "__main__":
    main()
