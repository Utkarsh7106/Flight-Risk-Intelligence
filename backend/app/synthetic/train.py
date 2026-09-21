"""Module 3 model training. Loads the full synthetic_employee dataset
(active + separated — separated rows are the labeled training examples),
fits a real classifier behind a real held-out test split, evaluates it
honestly, then refits on the full dataset and computes real per-employee
SHAP explanations for the active ("current workforce") subset only —
those are what the demo API/UI actually serve. See MODULE3_REFERENCE.md
for why predictions/SHAP are computed here, once, rather than live per
request.

Requires requirements-ml.txt (numpy/scikit-learn/shap) — NOT part of the
app's runtime requirements.txt. Run after app/synthetic/generate.py:

    cd backend && source .venv/bin/activate && pip install -r requirements-ml.txt
    python -m app.synthetic.train
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.synthetic_employee import SyntheticEmployee
from app.synthetic.features import FEATURE_LABELS, FEATURE_ORDER, RawSignals, compute_features, grade_medians

AS_OF = dt.date.today()
ML_RANDOM_STATE = 20260921
TEST_SIZE = 0.2

# Predicted-probability cut points for the demo's risk bands. NOT Module
# 2's 0-100 scale thresholds (35/60/80) — those were tuned for a bounded
# weighted-average score, not a probability with a ~17% base rate;
# reusing them here would put nearly everyone in "low" and say nothing
# useful. These were chosen by inspecting this model's actual predicted-
# probability distribution on the active set (see the printed percentile
# summary below) so the four bands are all meaningfully populated.
BAND_THRESHOLDS = [(0.12, "low"), (0.22, "medium"), (0.38, "high")]  # else "critical"
BAND_LABELS = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}

TOP_DRIVERS = 4


def _risk_band(probability: float) -> str:
    for threshold, band in BAND_THRESHOLDS:
        if probability < threshold:
            return band
    return "critical"


def _row_to_signals(row: SyntheticEmployee) -> RawSignals:
    return RawSignals(
        date_of_joining=row.date_of_joining,
        grade=row.grade,
        last_promotion_date=row.last_promotion_date,
        last_increment_date=row.last_increment_date,
        ctc_annual=float(row.ctc_annual),
        performance_rating=float(row.performance_rating),
        engagement_score=float(row.engagement_score),
        manager_effectiveness_score=float(row.manager_effectiveness_score),
        overtime=row.overtime,
        job_satisfaction_score=float(row.job_satisfaction_score),
        distance_from_home_km=float(row.distance_from_home_km),
    )


def _explanation_for(feature_name: str, value: float, shap_value: float) -> str:
    direction = "increased" if shap_value > 0 else "reduced"
    if feature_name == "overtime":
        detail = "frequent overtime" if value >= 0.5 else "no regular overtime"
    elif feature_name == "grade_ordinal":
        detail = f"grade level {int(value)}"
    elif feature_name in ("months_since_promotion", "months_since_increment"):
        detail = f"{value:.0f} months"
    elif feature_name == "tenure_years":
        detail = f"{value:.1f} years tenure"
    elif feature_name == "ctc_ratio_to_grade_median":
        detail = f"pay at {value * 100:.0f}% of grade-peer median"
    elif feature_name == "performance_rating":
        detail = f"rating {value:.1f}"
    else:
        detail = f"{value:.0f}"
    return f"{FEATURE_LABELS[feature_name]} ({detail}) {direction} predicted risk"


def build_dataset(rows: list[SyntheticEmployee]) -> tuple[np.ndarray, np.ndarray, list[SyntheticEmployee]]:
    signals = [_row_to_signals(r) for r in rows]
    medians = grade_medians(signals)
    features = [compute_features(s, AS_OF, medians[s.grade]) for s in signals]
    x = np.array([f.to_vector() for f in features], dtype=float)
    y = np.array([1 if r.employment_status == "separated" else 0 for r in rows], dtype=int)
    return x, y, rows


def train_and_evaluate(x: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=TEST_SIZE, stratify=y, random_state=ML_RANDOM_STATE
    )

    eval_model = RandomForestClassifier(
        n_estimators=300, max_depth=6, min_samples_leaf=5, random_state=ML_RANDOM_STATE
    )
    eval_model.fit(x_train, y_train)

    test_proba = eval_model.predict_proba(x_test)[:, 1]
    print("=== Held-out test set evaluation (never seen during training) ===")
    print(f"ROC-AUC: {roc_auc_score(y_test, test_proba):.3f} (0.5 = no better than chance, 1.0 = perfect)")

    # The model's default 0.5 decision threshold is meaningless on a ~17%
    # base rate (it predicts "stayed" for nearly everyone and reports a
    # hollow ~83% "accuracy"). Report precision/recall instead at a
    # base-rate-matched operating point: flag the top-N% highest-risk
    # test employees, where N = the test set's actual departure rate —
    # i.e. "if we flagged as many people as actually left, how many of
    # our flags were right, and how many actual leavers did we catch."
    flag_rate = y_test.mean()
    cutoff = np.quantile(test_proba, 1 - flag_rate)
    flagged = test_proba >= cutoff
    true_positives = int(np.sum(flagged & (y_test == 1)))
    precision = true_positives / max(1, int(flagged.sum()))
    recall = true_positives / max(1, int(y_test.sum()))
    print(
        f"At a top-{flag_rate:.0%}-by-risk operating point: "
        f"precision={precision:.2f}, recall={recall:.2f} "
        f"(vs. {flag_rate:.2f} precision from flagging at random)"
    )

    # Standard practice: use the held-out split purely to get an honest
    # accuracy/AUC read, then refit on 100% of the data for the model that
    # actually serves predictions — the eval numbers above are what
    # describe this model's real-world reliability, not the refit itself.
    final_model = RandomForestClassifier(
        n_estimators=300, max_depth=6, min_samples_leaf=5, random_state=ML_RANDOM_STATE
    )
    final_model.fit(x, y)
    return final_model


def score_active_employees(
    model: RandomForestClassifier, x: np.ndarray, rows: list[SyntheticEmployee]
) -> list[dict]:
    active_indices = [i for i, r in enumerate(rows) if r.employment_status == "active"]
    x_active = x[active_indices]

    probabilities = model.predict_proba(x_active)[:, 1]

    explainer = shap.TreeExplainer(model)
    shap_output = explainer.shap_values(x_active)
    # RandomForestClassifier binary output: shap_values may come back as a
    # list [class_0, class_1] (older SHAP) or a single (n, features, 2)
    # array (newer SHAP) — normalize to "contribution toward class 1 (left)".
    if isinstance(shap_output, list):
        shap_for_positive_class = shap_output[1]
    elif shap_output.ndim == 3:
        shap_for_positive_class = shap_output[:, :, 1]
    else:
        shap_for_positive_class = shap_output

    updates = []
    for local_i, row_i in enumerate(active_indices):
        row = rows[row_i]
        probability = float(probabilities[local_i])
        feature_vector = x_active[local_i]
        shap_row = shap_for_positive_class[local_i]

        ranked = sorted(
            zip(FEATURE_ORDER, feature_vector, shap_row), key=lambda t: abs(t[2]), reverse=True
        )[:TOP_DRIVERS]
        drivers = [
            {
                "feature": name,
                "label": FEATURE_LABELS[name],
                "value": round(float(value), 2),
                "shap_value": round(float(shap_value), 4),
                "explanation": _explanation_for(name, float(value), float(shap_value)),
            }
            for name, value, shap_value in ranked
        ]

        updates.append(
            {
                "id": row.id,
                "predicted_probability": round(probability, 4),
                "risk_band": _risk_band(probability),
                "shap_drivers": drivers,
            }
        )
    return updates


def main() -> None:
    url = settings.migrations_database_url or settings.database_url
    engine = create_engine(url)

    with Session(engine) as db:
        rows = list(db.scalars(select(SyntheticEmployee)))
        if not rows:
            raise RuntimeError("No synthetic_employee rows found — run app.synthetic.generate first.")

        x, y, rows = build_dataset(rows)
        print(f"Dataset: {len(rows)} rows, {int(y.sum())} labeled 'left' ({y.mean():.1%})")

        model = train_and_evaluate(x, y)
        updates = score_active_employees(model, x, rows)

        band_counts: dict[str, int] = {}
        for u in updates:
            band_counts[u["risk_band"]] = band_counts.get(u["risk_band"], 0) + 1
        print(f"Scored {len(updates)} active employees. Band distribution: {band_counts}")

        db.bulk_update_mappings(SyntheticEmployee, updates)
        db.commit()
        print("Persisted predicted_probability/risk_band/shap_drivers to synthetic_employee.")


if __name__ == "__main__":
    main()
