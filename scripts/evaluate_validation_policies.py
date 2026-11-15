
import json
import re
import sys
import unicodedata
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    balanced_accuracy_score,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import main

DATA = ROOT / "data"
OUT = ROOT / "evaluation_results"
OUT.mkdir(exist_ok=True)

THRESHOLDS = [0.05, 0.10, 0.14, 0.20, 0.30, 0.50]


def normalize(value):
    value = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", " ", value).strip().casefold()


def load_job_data(filename):
    df = pd.read_csv(DATA / filename)

    if not {"text", "label"}.issubset(df.columns):
        raise ValueError(f"{filename} needs text and label columns")

    df["text"] = df["text"].fillna("").astype(str).str.strip()
    df = df[df["text"] != ""].copy()
    df["label"] = pd.to_numeric(df["label"], errors="raise").astype(int)
    df["_norm"] = df["text"].map(normalize)

    if "source" in df.columns:
        df = df[
            df["source"].astype(str).str.strip().str.lower() == "job"
        ].copy()

    return df


def clean_validation():
    development = load_job_data("development_dataset_v4.csv")
    training = load_job_data("scamshield_train.csv")
    validation = load_job_data("scamshield_validation.csv")

    development = development.drop_duplicates("_norm")
    training = training.drop_duplicates("_norm")

    forbidden = set(development["_norm"]) | set(training["_norm"])

    validation = validation[
        ~validation["_norm"].isin(forbidden)
    ].drop_duplicates("_norm").reset_index(drop=True)

    if validation["_norm"].duplicated().any():
        raise RuntimeError("Validation contains duplicate normalized text")

    if set(validation["_norm"]) & forbidden:
        raise RuntimeError("Validation overlaps training data")

    if not validation["label"].isin([0, 1]).all():
        raise ValueError("Expected binary labels 0 and 1")

    return validation


def enrichment_patches():
    return [
        patch.object(main, "extract_emails", lambda text: []),
        patch.object(main, "extract_domains", lambda text: []),
        patch.object(main, "extract_company_name", lambda text: None),
        patch.object(
            main,
            "detect_careers_page",
            lambda text, domain: {
                "present": False, "url": None, "method": "none"
            },
        ),
        patch.object(
            main, "get_active_job_postings", lambda url: {"count": 0}
        ),
        patch.object(main, "extract_github_org", lambda text: None),
    ]


def get_predictions(validation):
    client = TestClient(main.app)
    results = []
    failures = []
    patches = enrichment_patches()

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        for i, row in validation.iterrows():
            try:
                response = client.post(
                    "/analyze",
                    json={
                        "text": row["text"],
                        "platform": "validation-policy-experiment",
                        "requester_id": "validation-policy-experiment",
                        "save_report": False,
                    },
                )

                if response.status_code != 200:
                    failures.append({
                        "row": int(i),
                        "status": response.status_code,
                        "detail": response.text[:300],
                    })
                    continue

                data = response.json()
                reasons = data.get("reasons") or []
                reason_ids = [
                    str(reason.get("rule_id", ""))
                    for reason in reasons
                ]

                results.append({
                    "row": int(i),
                    "true_label": int(row["label"]),
                    "text": row["text"],
                    "ml_probability": float(data["ml_probability"]),
                    "rule_score": float(data["rule_score"]),
                    "final_score": float(data["final_score"]),
                    "current_risk": str(data["risk_level"]).lower(),
                    "has_r01": "R01" in reason_ids,
                    "reason_ids": ",".join(reason_ids),
                })

            except Exception as exc:
                failures.append({
                    "row": int(i),
                    "error": repr(exc),
                })

            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(validation)} rows")

    if failures:
        (OUT / "validation_policy_failures.json").write_text(
            json.dumps(failures, indent=2),
            encoding="utf-8",
        )
        print(f"API failures: {len(failures)}")

    if not results:
        raise RuntimeError("No validation predictions succeeded")

    if failures:
        raise RuntimeError(
            "Some rows failed. Inspect validation_policy_failures.json "
            "before using these results."
        )

    return pd.DataFrame(results)


def evaluate_policy(y_true, flagged):
    flagged = pd.Series(flagged, index=y_true.index).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true, flagged, labels=[0, 1]
    ).ravel()

    return {
        "precision": round(
            precision_score(y_true, flagged, zero_division=0), 4
        ),
        "recall": round(
            recall_score(y_true, flagged, zero_division=0), 4
        ),
        "f1": round(f1_score(y_true, flagged, zero_division=0), 4),
        "balanced_accuracy": round(
            balanced_accuracy_score(y_true, flagged), 4
        ),
        "TP": int(tp),
        "FP": int(fp),
        "FN": int(fn),
        "TN": int(tn),
    }


def main_run():
    validation = clean_validation()
    print("Clean validation rows:", len(validation))
    print(
        "Label counts:",
        validation["label"].value_counts().sort_index().to_dict(),
    )

    df = get_predictions(validation)
    df.to_csv(
        OUT / "validation_policy_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )

    y = df["true_label"]

    # Existing API decision for comparison.
    df["current_flagged"] = df["current_risk"].isin(
        ["medium", "high"]
    ).astype(int)

    report = {
        "validation_rows": int(len(df)),
        "label_counts": {
            str(k): int(v)
            for k, v in y.value_counts().sort_index().items()
        },
        "policies": [],
        "interpretation": (
            "All candidate policies retain R01 as a High-risk override. "
            "ML thresholds are experimental and are not production changes."
        ),
    }

    current = evaluate_policy(y, df["current_flagged"])
    report["current_api_medium_or_high"] = current

    for threshold in THRESHOLDS:
        # A listing is flagged if its ML probability meets the threshold
        # OR the current API triggered the R01 override.
        flagged = (
            (df["ml_probability"] >= threshold) | df["has_r01"]
        ).astype(int)

        result = evaluate_policy(y, flagged)
        result["policy"] = "ml_threshold_or_R01"
        result["threshold"] = threshold
        report["policies"].append(result)

    # Illustrative three-band mapping for inspection only:
    # High if R01 or probability >= 0.20;
    # Medium if probability >= 0.10;
    # Low otherwise.
    # These cutoffs are candidates, not a recommendation yet.
    experimental_risk = []
    for _, row in df.iterrows():
        p = row["ml_probability"]
        if row["has_r01"] or p >= 0.20:
            experimental_risk.append("high")
        elif p >= 0.10:
            experimental_risk.append("medium")
        else:
            experimental_risk.append("low")

    df["experimental_risk"] = experimental_risk
    df.to_csv(
        OUT / "validation_policy_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )

    report["illustrative_three_band_policy"] = {
        "description": (
            "High: R01 or ML probability >= 0.20; "
            "Medium: ML probability >= 0.10; Low otherwise."
        ),
        "high_only": evaluate_policy(
            y, (df["experimental_risk"] == "high").astype(int)
        ),
        "medium_or_high": evaluate_policy(
            y, df["experimental_risk"].isin(
                ["medium", "high"]
            ).astype(int)
        ),
        "risk_counts": {
            str(k): int(v)
            for k, v in df["experimental_risk"].value_counts().items()
        },
    }

    (OUT / "validation_policy_metrics.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n=== CURRENT API: MEDIUM OR HIGH ===")
    print(json.dumps(current, indent=2))

    print("\n=== ML THRESHOLD + R01 POLICY COMPARISON ===")
    print(pd.DataFrame(report["policies"]).to_string(index=False))

    print("\n=== ILLUSTRATIVE THREE-BAND POLICY ===")
    print(json.dumps(report["illustrative_three_band_policy"], indent=2))

    print("\nSaved:")
    print(OUT / "validation_policy_metrics.json")
    print(OUT / "validation_policy_predictions.csv")


if __name__ == "__main__":
    main_run()
