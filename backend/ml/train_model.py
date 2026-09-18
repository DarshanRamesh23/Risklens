"""
Trains a small logistic regression model that outputs a PRIOR probability of
"material risk" from structured vendor attributes only (no document text).
This prior is what gets injected into the LLM agent's prompt -- the model's
job is narrow: turn a few structured facts into a calibrated starting point,
not to replace the document-level reasoning.

Run: python ml/train_model.py
Produces: ml/model.pkl, ml/feature_meta.json, ml/synthetic_vendors.csv

NOTE: the training data here is synthetic (generated below) because this is
a portfolio project without access to real vendor risk outcomes. That's worth
saying out loud in an interview -- the pipeline (features -> encode -> train
-> calibrate -> serialize -> load in the API) is the real deliverable; swapping
in a real historical dataset would be a drop-in replacement for this script.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RNG = np.random.default_rng(42)
INDUSTRIES = ["fintech", "healthcare", "saas", "logistics", "manufacturing", "retail"]
GEOS = ["us", "eu", "apac", "latam", "other"]

# rough, illustrative base risk weights per category -- stand-ins for what
# would come from real historical loss/incident data
INDUSTRY_RISK = {"fintech": 0.55, "healthcare": 0.5, "saas": 0.3, "logistics": 0.25, "manufacturing": 0.3, "retail": 0.2}
GEO_RISK = {"us": 0.2, "eu": 0.2, "apac": 0.3, "latam": 0.4, "other": 0.45}


def generate_synthetic_data(n: int = 2000) -> pd.DataFrame:
    industries = RNG.choice(INDUSTRIES, size=n)
    geos = RNG.choice(GEOS, size=n)
    past_incidents = RNG.poisson(0.6, size=n)
    contract_value = RNG.lognormal(mean=11, sigma=1.2, size=n)  # right-skewed $ values

    logits = np.array([
        3.2 * INDUSTRY_RISK[ind] + 2.0 * GEO_RISK[geo] + 0.9 * inc + 0.15 * np.log1p(cv) - 4.0
        for ind, geo, inc, cv in zip(industries, geos, past_incidents, contract_value)
    ])
    probs = 1 / (1 + np.exp(-logits))
    labels = RNG.binomial(1, probs)

    return pd.DataFrame({
        "industry": industries,
        "geography": geos,
        "past_incidents": past_incidents,
        "contract_value_usd": contract_value,
        "material_risk_label": labels,
    })


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["industry", "geography"]),
        ("num", StandardScaler(), ["past_incidents", "contract_value_usd"]),
    ])
    return Pipeline([
        ("preprocess", preprocessor),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])


def main() -> None:
    out_dir = Path(__file__).parent
    df = generate_synthetic_data()
    df.to_csv(out_dir / "synthetic_vendors.csv", index=False)

    X = df[["industry", "geography", "past_incidents", "contract_value_usd"]]
    y = df["material_risk_label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    probs = pipeline.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, preds))
    print(f"ROC AUC: {roc_auc_score(y_test, probs):.3f}")

    joblib.dump(pipeline, out_dir / "model.pkl")
    with open(out_dir / "feature_meta.json", "w") as f:
        json.dump({"industries": INDUSTRIES, "geographies": GEOS}, f, indent=2)

    print(f"Saved model to {out_dir / 'model.pkl'}")


if __name__ == "__main__":
    main()
