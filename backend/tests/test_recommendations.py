"""Module 2 Part 5: retention recommendation rule coverage.

ScoreResult objects here are constructed directly with crafted driver
lists, independent of score_employee()'s formula, so these tests exercise
only the recommendation rules themselves (app/scoring/recommendations.py).
"""

from __future__ import annotations

from app.scoring.model import DriverContribution, RiskBand, ScoreResult
from app.scoring.recommendations import recommend


def _driver(key: str, risk_points: float, weight_share: float = 0.3) -> DriverContribution:
    return DriverContribution(key=key, label=key, explanation="", risk_points=risk_points, weight_share=weight_share)


def _result(*drivers: DriverContribution) -> ScoreResult:
    return ScoreResult(score=70.0, band=RiskBand.HIGH, band_label="High", drivers=list(drivers), data_completeness=1.0)


def test_recognition_gap_triggers_career_mobility_and_suppresses_promotion_pathing():
    result = _result(
        _driver("performance_recognition_gap", 100.0),
        _driver("promotion_stagnation", 80.0),
    )
    recs = recommend(result)
    keys = [r.key for r in recs]
    assert "career_mobility_conversation" in keys
    assert "promotion_pathing_conversation" not in keys


def test_promotion_stagnation_alone_triggers_pathing_conversation():
    result = _result(_driver("promotion_stagnation", 65.0))
    recs = recommend(result)
    assert [r.key for r in recs] == ["promotion_pathing_conversation"]


def test_compensation_dominant_triggers_review_independent_of_promotion():
    result = _result(
        _driver("promotion_stagnation", 65.0),
        _driver("compensation_trajectory", 55.0),
    )
    recs = recommend(result)
    keys = {r.key for r in recs}
    assert "promotion_pathing_conversation" in keys
    assert "compensation_review" in keys
    assert len(recs) == 2


def test_engagement_and_manager_both_dominant_merge_into_relationship_conversation():
    result = _result(
        _driver("engagement", 60.0),
        _driver("manager_effectiveness", 70.0),
    )
    recs = recommend(result)
    keys = [r.key for r in recs]
    assert keys == ["manager_relationship_conversation"]
    assert "manager_coaching" not in keys
    assert "engagement_checkin" not in keys


def test_manager_dominant_alone_triggers_manager_coaching():
    result = _result(_driver("manager_effectiveness", 65.0), _driver("engagement", 20.0))
    recs = recommend(result)
    assert [r.key for r in recs] == ["manager_coaching"]


def test_engagement_dominant_alone_triggers_checkin():
    result = _result(_driver("engagement", 65.0), _driver("manager_effectiveness", 10.0))
    recs = recommend(result)
    assert [r.key for r in recs] == ["engagement_checkin"]


def test_no_dominant_driver_falls_back_to_monitor():
    result = _result(_driver("promotion_stagnation", 20.0), _driver("engagement", 15.0))
    recs = recommend(result)
    assert [r.key for r in recs] == ["monitor"]


def test_all_four_rule_groups_can_fire_simultaneously():
    result = _result(
        _driver("promotion_stagnation", 60.0),
        _driver("compensation_trajectory", 60.0),
        _driver("engagement", 60.0),
        _driver("manager_effectiveness", 60.0),
    )
    recs = recommend(result)
    keys = {r.key for r in recs}
    assert keys == {"promotion_pathing_conversation", "compensation_review", "manager_relationship_conversation"}


def test_identical_driver_profile_always_produces_identical_recommendations():
    result_a = _result(_driver("engagement", 90.0))
    result_b = _result(_driver("engagement", 90.0))
    assert recommend(result_a) == recommend(result_b)
