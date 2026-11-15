
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "evaluation_results" / "validation_policy_predictions.csv"
OUT = ROOT / "evaluation_results"

df = pd.read_csv(FILE)
df["true_label"] = df["true_label"].astype(int)
df["ml_probability"] = pd.to_numeric(df["ml_probability"])
df["has_r01"] = df["has_r01"].astype(str).str.lower().eq("true")

# Candidate policy: High at 0.20 or R01; Medium at 0.10.
df["candidate_flagged"] = (
    (df["ml_probability"] >= 0.10) | df["has_r01"]
)

false_positives = df[
    (df["true_label"] == 0) & df["candidate_flagged"]
].sort_values("ml_probability", ascending=False)

missed_scams = df[
    (df["true_label"] == 1) & ~df["candidate_flagged"]
].sort_values("ml_probability", ascending=True)

columns = [
    "true_label", "ml_probability", "rule_score",
    "final_score", "current_risk", "has_r01",
    "reason_ids", "text"
]
columns = [c for c in columns if c in df.columns]

false_positives[columns].to_csv(
    OUT / "validation_false_positives.csv",
    index=False,
    encoding="utf-8-sig",
)
missed_scams[columns].to_csv(
    OUT / "validation_missed_scams.csv",
    index=False,
    encoding="utf-8-sig",
)

print("Candidate false positives:", len(false_positives))
print("Candidate missed scams:", len(missed_scams))

print("\n=== TOP 15 FALSE POSITIVES ===")
for _, row in false_positives.head(15).iterrows():
    print(
        f"\nProbability={row['ml_probability']:.3f} | "
        f"R01={row['has_r01']} | "
        f"Rules={row.get('reason_ids', '')}"
    )
    print(str(row["text"])[:450].replace("\n", " "))

print("\n=== MISSED SCAMS ===")
for _, row in missed_scams.iterrows():
    print(
        f"\nProbability={row['ml_probability']:.3f} | "
        f"Rules={row.get('reason_ids', '')}"
    )
    print(str(row["text"])[:450].replace("\n", " "))

print("\nSaved review files in:", OUT)
