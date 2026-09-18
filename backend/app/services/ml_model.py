"""
Loads the trained logistic regression pipeline and produces the ML prior
used to seed the LLM agent's prompt (see services/agent.py).
"""
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from app.config import settings

MODEL_PATH = Path(__file__).resolve().parents[2] / settings.ml_model_path


@lru_cache(maxsize=1)
def get_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No trained model at {MODEL_PATH}. Run `python ml/train_model.py` first."
        )
    return joblib.load(MODEL_PATH)


def predict_prior_risk(industry: str, geography: str, past_incidents: int, contract_value_usd: float) -> dict:
    model = get_model()
    row = pd.DataFrame([{
        "industry": industry,
        "geography": geography,
        "past_incidents": past_incidents,
        "contract_value_usd": contract_value_usd,
    }])
    prob = float(model.predict_proba(row)[0, 1])

    # crude "main driver" explanation for the prompt / UI -- not a full SHAP
    # explanation, but enough to give the agent (and the analyst) a reason,
    # not just a number. A real MLOps version would swap this for SHAP values.
    driver = "past incidents" if past_incidents >= 2 else (
        "industry risk tier" if industry in ("fintech", "healthcare") else "geography"
    )
    return {"prior_risk_probability": round(prob, 3), "main_driver": driver}
