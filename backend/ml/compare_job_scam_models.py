"""Compare Job Scam Radar's small dataset against ScamShield job-only training.

Reads:
  data/development_dataset_v4.csv
  data/scamshield_train.csv
  data/scamshield_validation.csv
  data/scamshield_test.csv

The script:
- trains two fresh TF-IDF + Logistic Regression models in memory;
- Model A uses the existing development dataset;
- Model B uses ScamShield train rows where source == "job" (no synthetic/SMS rows);
- uses validation data to choose an F1-based threshold;
- removes normalized exact-text overlaps across train/validation/test;
- evaluates both models on the SAME clean job-only test set;
- never reads, overwrites, or saves your project's existing trained model.

Labels: 0 = safe/legitimate, 1 = scam.
"""

from __future__ import annotations

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
DATA_DIR = PROJECT_ROOT / "data"
DEV_PATH = DATA_DIR / "development_dataset_v4.csv"
TRAIN_PATH = DATA_DIR / "scamshield_train.csv"
VALIDATION_PATH = DATA_DIR / "scamshield_validation.csv"
TEST_PATH = DATA_DIR / "scamshield_test.csv"


def normalize_text(value: object) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", " ", value).strip().casefold()


def load_csv(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing file: {path}\n"
            "Copy the downloaded file into the project's data folder using the "
            "filename shown in the error."
        )
    frame = pd.read_csv(path)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            f"{path.name} is missing required columns {sorted(missing)}. "
            f"Columns found: {list(frame.columns)}"
        )
    frame = frame.copy()
    frame["text"] = frame["text"].fillna("").astype(str).str.strip()
    frame["label"] = pd.to_numeric(frame["label"], errors="raise").astype(int)
    frame = frame[frame["text"] != ""].copy()
    if not set(frame["label"].unique()).issubset({0, 1}):
        raise ValueError(f"{path.name} must use labels 0=safe and 1=scam.")
    frame["_norm"] = frame["text"].map(normalize_text)
    return frame


def require_both_labels(frame: pd.DataFrame, name: str) -> None:
    labels = set(frame["label"].unique())
    if labels != {0, 1}:
        raise ValueError(
            f"{name} must contain both labels 0 and 1 after filtering. "
            f"Found counts: {frame['label'].value_counts().to_dict()}"
        )


def make_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


def select_f1_threshold(y_true, probabilities) -> tuple[float, float]:
    best_threshold = 0.50
    best_f1 = -1.0
    # Use a fixed grid so the threshold choice is reproducible.
    for threshold in [i / 100 for i in range(5, 96)]:
        predictions = (probabilities >= threshold).astype(int)
        score = f1_score(y_true, predictions, zero_division=0)
        # On a tie, prefer the threshold with higher scam recall.
        if score > best_f1:
            best_f1 = score
            best_threshold = threshold
        elif score == best_f1:
            current_recall = recall_score(
                y_true, predictions, zero_division=0
            )
            old_predictions = (probabilities >= best_threshold).astype(int)
            old_recall = recall_score(
                y_true, old_predictions, zero_division=0
            )
            if current_recall > old_recall:
                best_threshold = threshold
    return best_threshold, best_f1


def report_metrics(name: str, y_true, probabilities, threshold: float) -> None:
    predictions = (probabilities >= threshold).astype(int)
    print("\n" + "=" * 76)
    print(name)
    print("=" * 76)
    print(f"Threshold:          {threshold:.2f}")
    print(f"Accuracy:           {accuracy_score(y_true, predictions):.4f}")
    print(f"Balanced accuracy:  {balanced_accuracy_score(y_true, predictions):.4f}")
    print(f"Scam precision:     {precision_score(y_true, predictions, zero_division=0):.4f}")
    print(f"Scam recall:        {recall_score(y_true, predictions, zero_division=0):.4f}")
    print(f"Scam F1-score:      {f1_score(y_true, predictions, zero_division=0):.4f}")
    try:
        print(f"ROC-AUC:            {roc_auc_score(y_true, probabilities):.4f}")
    except ValueError:
        print("ROC-AUC:            unavailable")
    print("\nClassification report:")
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
    print("Confusion matrix (rows=actual [0,1], columns=predicted [0,1]):")
    print(confusion_matrix(y_true, predictions, labels=[0, 1]))


def main() -> int:
    try:
        dev = load_csv(DEV_PATH, {"text", "label"})
        scam_train = load_csv(TRAIN_PATH, {"text", "label", "source"})
        validation = load_csv(VALIDATION_PATH, {"text", "label", "source"})
        test = load_csv(TEST_PATH, {"text", "label", "source"})
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    # Only job examples are used for the external training/validation/test splits.
    scam_train = scam_train[
        scam_train["source"].astype(str).str.strip().str.lower() == "job"
    ].copy()
    validation = validation[
        validation["source"].astype(str).str.strip().str.lower() == "job"
    ].copy()
    test = test[
        test["source"].astype(str).str.strip().str.lower() == "job"
    ].copy()

    # Keep each training split internally unique.
    dev = dev.drop_duplicates(subset="_norm", keep="first").copy()
    scam_train = scam_train.drop_duplicates(subset="_norm", keep="first").copy()

    # Validation must be independent of BOTH training options.
    all_training_texts = set(dev["_norm"]) | set(scam_train["_norm"])
    validation_before = len(validation)
    validation = validation[~validation["_norm"].isin(all_training_texts)].copy()
    validation = validation.drop_duplicates(subset="_norm", keep="first").copy()
    validation_removed = validation_before - len(validation)

    # Test must be independent of both training sets and the remaining validation set.
    test_before = len(test)
    forbidden_test_texts = (
        all_training_texts | set(validation["_norm"])
    )
    test = test[~test["_norm"].isin(forbidden_test_texts)].copy()
    test = test.drop_duplicates(subset="_norm", keep="first").copy()
    test_removed = test_before - len(test)

    require_both_labels(dev, "Existing development dataset")
    require_both_labels(scam_train, "ScamShield job training subset")
    require_both_labels(validation, "Clean job validation subset")
    require_both_labels(test, "Clean job test subset")

    print("=" * 76)
    print("JOB SCAM RADAR: CLEAN SPLIT COMPARISON")
    print("=" * 76)
    print("No existing saved model is loaded, changed, or overwritten.")
    print("\nRows used:")
    print(f"Existing development dataset: {len(dev)}")
    print(f"ScamShield job-only training:  {len(scam_train)}")
    print(f"Validation job rows used:     {len(validation)}")
    print(f"Validation rows removed due to train overlap/duplicates: {validation_removed}")
    print(f"Test job rows before cleaning: {test_before}")
    print(f"Test rows removed due to train/validation overlap/duplicates: {test_removed}")
    print(f"Clean test job rows used:      {len(test)}")
    print("\nLabel counts (0=safe, 1=scam):")
    print(f"Existing development: {dev['label'].value_counts().sort_index().to_dict()}")
    print(f"ScamShield training:  {scam_train['label'].value_counts().sort_index().to_dict()}")
    print(f"Validation:           {validation['label'].value_counts().sort_index().to_dict()}")
    print(f"Clean test:           {test['label'].value_counts().sort_index().to_dict()}")

    # Final sanity checks for normalized text overlap.
    assert not (set(dev["_norm"]) & set(validation["_norm"]))
    assert not (set(scam_train["_norm"]) & set(validation["_norm"]))
    assert not (set(dev["_norm"]) & set(test["_norm"]))
    assert not (set(scam_train["_norm"]) & set(test["_norm"]))
    assert not (set(validation["_norm"]) & set(test["_norm"]))

    y_val = validation["label"].to_numpy()
    y_test = test["label"].to_numpy()

    # Model A: current small development dataset.
    model_small = make_model()
    model_small.fit(dev["text"], dev["label"])
    small_val_prob = model_small.predict_proba(validation["text"])[:, 1]
    small_threshold, small_val_f1 = select_f1_threshold(y_val, small_val_prob)
    small_test_prob = model_small.predict_proba(test["text"])[:, 1]

    # Model B: larger ScamShield job-only training data, no synthetic or SMS rows.
    model_large = make_model()
    model_large.fit(scam_train["text"], scam_train["label"])
    large_val_prob = model_large.predict_proba(validation["text"])[:, 1]
    large_threshold, large_val_f1 = select_f1_threshold(y_val, large_val_prob)
    large_test_prob = model_large.predict_proba(test["text"])[:, 1]

    print("\nValidation-selected thresholds (chosen on validation only):")
    print(f"Small model threshold: {small_threshold:.2f} (validation F1={small_val_f1:.4f})")
    print(f"Large model threshold: {large_threshold:.2f} (validation F1={large_val_f1:.4f})")

    report_metrics(
        "MODEL A — Existing 180-row development dataset (threshold 0.50)",
        y_test, small_test_prob, 0.50
    )
    report_metrics(
        "MODEL A — Existing 180-row development dataset (validation-selected threshold)",
        y_test, small_test_prob, small_threshold
    )
    report_metrics(
        "MODEL B — ScamShield job-only training subset (threshold 0.50)",
        y_test, large_test_prob, 0.50
    )
    report_metrics(
        "MODEL B — ScamShield job-only training subset (validation-selected threshold)",
        y_test, large_test_prob, large_threshold
    )

    print("\nINTERPRETATION")
    print(
        "- Compare scam recall, precision, F1, balanced accuracy and ROC-AUC, not accuracy alone.\n"
        "- Thresholds were selected on validation data, not on the final test data.\n"
        "- This tests a text classifier only, not the full Job Scam Radar hybrid pipeline.\n"
        "- Dataset labels have not been independently verified; report this limitation.\n"
        "- The external dataset is not necessarily representative of Indian job scams."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
