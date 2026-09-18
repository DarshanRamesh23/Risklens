from fastapi import APIRouter, HTTPException

from app.db.postgres import Vendor, get_session
from app.schemas import ScoreResponse
from app.services.agent import run_agent_for_vendor
from app.services.ml_model import predict_prior_risk

router = APIRouter(prefix="/api/score", tags=["scoring"])


def _combine_to_final_score(ml_prior: float, findings) -> tuple[float, str]:
    """
    Final score = ML prior, adjusted upward by grounded high/medium findings.
    This is intentionally a simple, explainable rule (not another black box)
    layered on top of two black-box-ish components -- the analyst should be
    able to see exactly why the number moved.
    """
    score = ml_prior
    for f in findings:
        if not f.grounded:
            continue
        if f.severity == "high":
            score = min(1.0, score + 0.2)
        elif f.severity == "medium":
            score = min(1.0, score + 0.08)

    tier = "low" if score < 0.33 else ("medium" if score < 0.66 else "high")
    return round(score, 3), tier


@router.post("/{vendor_id}", response_model=ScoreResponse)
def score_vendor(vendor_id: int):
    session = get_session()
    try:
        vendor = session.get(Vendor, vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        ml_result = predict_prior_risk(
            vendor.industry, vendor.geography, vendor.past_incidents, vendor.contract_value_usd
        )

        findings = run_agent_for_vendor(vendor_id, ml_result)

        final_score, final_tier = _combine_to_final_score(ml_result["prior_risk_probability"], findings)

        vendor.ml_prior_risk_prob = ml_result["prior_risk_probability"]
        vendor.final_risk_score = final_score
        vendor.final_risk_tier = final_tier
        session.commit()

        return {
            "vendor_id": vendor_id,
            "ml_prior_risk_prob": ml_result["prior_risk_probability"],
            "ml_main_driver": ml_result["main_driver"],
            "final_risk_score": final_score,
            "final_risk_tier": final_tier,
            "findings": findings,
        }
    finally:
        session.close()
