from dataclasses import dataclass

from app.routers.scoring import _combine_to_final_score


@dataclass
class FakeFinding:
    severity: str
    grounded: bool


def test_no_findings_keeps_ml_prior():
    score, tier = _combine_to_final_score(0.2, [])
    assert score == 0.2
    assert tier == "low"


def test_ungrounded_findings_do_not_move_score():
    findings = [FakeFinding(severity="high", grounded=False)]
    score, tier = _combine_to_final_score(0.2, findings)
    assert score == 0.2


def test_grounded_high_finding_pushes_up_tier():
    findings = [FakeFinding(severity="high", grounded=True)]
    score, tier = _combine_to_final_score(0.5, findings)
    assert score == 0.7
    assert tier == "high"


def test_score_caps_at_one():
    findings = [FakeFinding(severity="high", grounded=True) for _ in range(10)]
    score, _ = _combine_to_final_score(0.9, findings)
    assert score == 1.0
