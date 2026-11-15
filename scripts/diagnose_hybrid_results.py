
from pathlib import Path
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "evaluation_results" / "hybrid_test_predictions.csv"

df = pd.read_csv(FILE)
df["true_label"] = df["true_label"].astype(int)
df["ml_probability"] = pd.to_numeric(
    df["ml_probability"], errors="coerce"
)
df["final_score"] = pd.to_numeric(
    df["final_score"], errors="coerce"
)
df["risk_level"] = df["risk_level"].astype(str).str.lower()

print("\n=== 1. ML PROBABILITY BY TRUE LABEL ===")
print(
    df.groupby("true_label")["ml_probability"]
    .describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9])
    .round(4)
    .to_string()
)

print("\n=== 2. FINAL SCORE BY TRUE LABEL ===")
print(
    df.groupby("true_label")["final_score"]
    .describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9])
    .round(2)
    .to_string()
)

print("\n=== 3. ML-ONLY THRESHOLD DIAGNOSTIC ===")
y = df["true_label"]
p = df["ml_probability"]

for threshold in [0.05, 0.10, 0.14, 0.20, 0.30, 0.50]:
    pred = (p >= threshold).astype(int)
    print(
        f"threshold={threshold:.2f} | "
        f"precision={precision_score(y, pred, zero_division=0):.3f} | "
        f"recall={recall_score(y, pred, zero_division=0):.3f} | "
        f"F1={f1_score(y, pred, zero_division=0):.3f} | "
        f"confusion_matrix={confusion_matrix(y, pred, labels=[0, 1]).tolist()}"
    )

print("\n=== 4. HYBRID RISK LEVEL BY TRUE LABEL ===")
print(pd.crosstab(
    df["true_label"],
    df["risk_level"],
    rownames=["true_label"],
    colnames=["risk_level"],
).to_string())

print("\n=== 5. RULE TRIGGERS BY TRUE LABEL ===")
if "reason_ids" in df.columns:
    for label, group in df.groupby("true_label"):
        counts = {}
        for value in group["reason_ids"].fillna(""):
            for rule in str(value).split(","):
                rule = rule.strip()
                if rule:
                    counts[rule] = counts.get(rule, 0) + 1
        print(f"Label {label}: {dict(sorted(counts.items()))}")

print("\n=== 6. SCAM EXAMPLES CLASSIFIED LOW ===")
cols = [
    c for c in [
        "true_label", "ml_probability", "rule_score",
        "final_score", "risk_level", "reason_ids", "text"
    ] if c in df.columns
]
missed = df[
    (df["true_label"] == 1) &
    (df["risk_level"] == "low")
].sort_values("ml_probability", ascending=False)

for _, row in missed.head(10).iterrows():
    print("\n---")
    for col in cols:
        value = row[col]
        if col == "text":
            value = str(value)[:500]
        print(f"{col}: {value}")
