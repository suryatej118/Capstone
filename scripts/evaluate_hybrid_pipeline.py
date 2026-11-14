

import json
import re
import sys
import unicodedata
from pathlib import Path
from unittest.mock import patch

# Ensure Python can import the project package when this file
# is executed directly from the scripts directory.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from fastapi.testclient import TestClient
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

from backend import main

DATA = ROOT / "data"
OUT = ROOT / "evaluation_results"
OUT.mkdir(exist_ok=True)


def normalize(value):
    value = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", " ", value).strip().casefold()


def load_job_data(filename):
    df = pd.read_csv(DATA / filename)

    required = {"text", "label"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"{filename} must contain columns: {sorted(required)}"
        )

    df["text"] = df["text"].fillna("").astype(str).str.strip()
    df = df[df["text"] != ""].copy()
    df["label"] = pd.to_numeric(df["label"], errors="raise").astype(int)
    df["_norm"] = df["text"].map(normalize)

    if "source" in df.columns:
        df = df[
            df["source"].astype(str).str.strip().str.lower() == "job"
        ].copy()

    return df


def build_clean_test():
    development = load_job_data("development_dataset_v4.csv")
    training = load_job_data("scamshield_train.csv")
    validation = load_job_data("scamshield_validation.csv")
    test = load_job_data("scamshield_test.csv")

    development = development.drop_duplicates("_norm")
    training = training.drop_duplicates("_norm")

    training_texts = (
        set(development["_norm"]) | set(training["_norm"])
    )

    validation = validation[
        ~validation["_norm"].isin(training_texts)
    ].drop_duplicates("_norm")

    test = test.drop_duplicates("_norm")
    forbidden = training_texts | set(validation["_norm"])
    test = test[~test["_norm"].isin(forbidden)].copy()

    overlap_train = set(test["_norm"]) & training_texts
    overlap_val = set(test["_norm"]) & set(validation["_norm"])

    if overlap_train or overlap_val:
        raise RuntimeError("Clean split overlap check failed.")

    test = test.reset_index(drop=True)
    test["text"] = test["text"].astype(str)

    return test


def mock_enrichment():
    """Prevent external enrichment calls during offline evaluation."""
    return [
        patch.object(main, "extract_emails", lambda text: []),
        patch.object(main, "extract_domains", lambda text: []),
        patch.object(main, "extract_company_name", lambda text: None),
        patch.object(
            main,
            "detect_careers_page",
            lambda text, domain: {
                "present": False,
                "url": None,
                "method": "none",
            },
        ),
        patch.object(
            main,
            "get_active_job_postings",
            lambda url: {"count": 0},
        ),
        patch.object(main, "extract_github_org", lambda text: None),
    ]


def metrics_for(y_true, y_pred):
    return {
        "precision": round(
            precision_score(y_true, y_pred, zero_division=0), 4
        ),
        "recall": round(
            recall_score(y_true, y_pred, zero_division=0), 4
        ),
        "f1": round(
            f1_score(y_true, y_pred, zero_division=0), 4
        ),
        "balanced_accuracy": round(
            balanced_accuracy_score(y_true, y_pred), 4
        ),
        "confusion_matrix_labels_0_1": confusion_matrix(
            y_true, y_pred, labels=[0, 1]
        ).tolist(),
    }


def main_run():
    test = build_clean_test()
    print(f"Clean test rows: {len(test)}")
    print("Ground-truth labels:", test["label"].value_counts().sort_index().to_dict())

    client = TestClient(main.app)
    results = []
    failures = []

    patches = mock_enrichment()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        for index, row in test.iterrows():
            try:
                response = client.post(
                    "/analyze",
                    json={
                        "text": row["text"],
                        "platform": "offline-evaluation",
                        "requester_id": "hybrid-evaluation",
                        "save_report": False,
                    },
                )

                if response.status_code != 200:
                    failures.append({
                        "row": int(index),
                        "status_code": response.status_code,
                        "detail": response.text[:500],
                    })
                    continue

                data = response.json()
                reasons = data.get("reasons") or []

                results.append({
                    "row": int(index),
                    "true_label": int(row["label"]),
                    "text": row["text"],
                    "rule_score": data.get("rule_score"),
                    "ml_probability": data.get("ml_probability"),
                    "final_score": data.get("final_score"),
                    "risk_level": data.get("risk_level"),
                    "confidence": data.get("confidence"),
                    "reason_ids": ",".join(
                        str(reason.get("rule_id", ""))
                        for reason in reasons
                    ),
                    "reason_text": " | ".join(
                        str(reason.get("description", reason.get("message", "")))
                        for reason in reasons
                    ),
                    "hiring_intent_score": data.get("hiring_intent_score"),
                    "hiring_intent_reasons": json.dumps(
                        data.get("hiring_intent_reasons", []),
                        ensure_ascii=False,
                    ),
                })

            except Exception as exc:
                failures.append({
                    "row": int(index),
                    "error": repr(exc),
                })

            if (index + 1) % 100 == 0:
                print(f"Processed {index + 1}/{len(test)} rows")

    results_df = pd.DataFrame(results)
    results_path = OUT / "hybrid_test_predictions.csv"
    results_df.to_csv(results_path, index=False, encoding="utf-8-sig")

    failure_path = OUT / "hybrid_test_failures.json"
    failure_path.write_text(
        json.dumps(failures, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if results_df.empty:
        raise RuntimeError(
            "No successful API predictions. Check hybrid_test_failures.json."
        )

    y_true = results_df["true_label"].astype(int)
    risk = results_df["risk_level"].fillna("").str.strip().str.lower()

    # Treat High risk as a positive scam detection.
    pred_high = risk.eq("high").astype(int)

    # Also measure a more sensitive policy: Medium OR High is flagged.
    pred_flagged = risk.isin(["medium", "high"]).astype(int)

    report = {
        "evaluation": "hybrid API endpoint; external enrichment mocked",
        "test_rows_expected": int(len(test)),
        "successful_predictions": int(len(results_df)),
        "failed_predictions": int(len(failures)),
        "ground_truth_label_counts": {
            str(k): int(v)
            for k, v in y_true.value_counts().sort_index().items()
        },
        "risk_level_counts": {
            str(k): int(v)
            for k, v in risk.value_counts().items()
        },
        "high_risk_only": metrics_for(y_true, pred_high),
        "medium_or_high_flagged": metrics_for(y_true, pred_flagged),
        "ml_probability_roc_auc": None,
        "classification_report_high_risk_only": classification_report(
            y_true,
            pred_high,
            labels=[0, 1],
            target_names=["safe", "scam"],
            zero_division=0,
            output_dict=True,
        ),
        "important_limitations": [
            "External enrichment was mocked and contributes no real evidence.",
            "These metrics evaluate API risk labels, not calibrated probabilities.",
            "The test set contains only the examples in the audited clean split.",
            "Source dataset labels may contain errors or domain-specific bias.",
        ],
    }

    # ROC-AUC of the ML probability is a separate diagnostic, not a
    # measure of the final hybrid risk-level decision.
    if (
        results_df["ml_probability"].notna().all()
        and y_true.nunique() == 2
    ):
        report["ml_probability_roc_auc"] = round(
            roc_auc_score(
                y_true,
                results_df["ml_probability"].astype(float),
            ),
            4,
        )

    report_path = OUT / "hybrid_test_metrics.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n=== HYBRID EVALUATION SUMMARY ===")
    print(json.dumps({
        "successful_predictions": report["successful_predictions"],
        "failed_predictions": report["failed_predictions"],
        "risk_level_counts": report["risk_level_counts"],
        "high_risk_only": report["high_risk_only"],
        "medium_or_high_flagged": report["medium_or_high_flagged"],
        "ml_probability_roc_auc": report["ml_probability_roc_auc"],
    }, indent=2))

    print("\nSaved:")
    print(results_path)
    print(report_path)
    print(failure_path)


if __name__ == "__main__":
    main_run()
