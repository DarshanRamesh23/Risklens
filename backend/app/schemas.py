from datetime import datetime

from pydantic import BaseModel


class VendorCreate(BaseModel):
    name: str
    industry: str
    geography: str
    past_incidents: int = 0
    contract_value_usd: float = 0


class VendorOut(BaseModel):
    id: int
    name: str
    industry: str
    geography: str
    past_incidents: int
    contract_value_usd: float
    ml_prior_risk_prob: float | None
    final_risk_score: float | None
    final_risk_tier: str | None

    class Config:
        from_attributes = True


class FindingOut(BaseModel):
    id: int
    severity: str
    summary: str
    vendor_quote: str | None
    policy_quote: str | None
    grounded: bool
    created_at: datetime

    class Config:
        from_attributes = True


class IngestResponse(BaseModel):
    detail: dict


class ScoreResponse(BaseModel):
    vendor_id: int
    ml_prior_risk_prob: float
    ml_main_driver: str
    final_risk_score: float
    final_risk_tier: str
    findings: list[FindingOut]
