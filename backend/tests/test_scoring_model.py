"""Module 2 Part 5: scoring math verified against hand-calculated values.

Every expected number here was derived independently, by hand, from the
formula documented in app/scoring/model.py's module docstring (linear
ramps between the low/high thresholds stated there, weighted average with
renormalization when a factor's data is missing) — not by calling
score_employee() and copying its output. If someone changes a weight or a
threshold in model.py without meaning to, these numbers stop matching.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.scoring.model import RiskBand, ScoringInputs, score_employee

AS_OF = dt.date(2026, 9, 21)


def test_low_risk_well_rewarded_average_performer():
    # promotion: 6 months since last promotion -> well under the 18-month
    #   floor -> risk 0
    # compensation: ratio 1,050,000 / 1,000,000 = 1.05 -> at the 1.05 "no
    #   risk" ceiling -> position risk 0; last raised 3 months ago -> under
    #   the 12-month floor -> momentum risk 0 -> avg 0
    # engagement 85 -> risk 100-85=15
    # manager effectiveness 88 -> risk 100-88=12
    # performance 3.2 < 4.0 strong-performer threshold -> gap not triggered -> risk 0
    # weights all present (0.30+0.25+0.22+0.15+0.08=1.00):
    #   score = 0*0.30 + 0*0.25 + 15*0.22 + 12*0.15 + 0*0.08 = 3.3 + 1.8 = 5.1
    inputs = ScoringInputs(
        as_of=AS_OF,
        date_of_joining=dt.date(2020, 1, 1),
        grade="L3",
        last_promotion_date=dt.date(2026, 3, 21),
        last_increment_date=dt.date(2026, 6, 21),
        ctc_annual=1_050_000,
        peer_median_ctc_at_grade=1_000_000,
        peer_group_size=5,
        performance_rating=3.2,
        engagement_score=85,
        manager_effectiveness_score=88,
    )
    result = score_employee(inputs)
    assert result.score == pytest.approx(5.1, abs=0.05)
    assert result.band == RiskBand.LOW
    assert result.data_completeness == pytest.approx(1.0)
    driver_keys = [d.key for d in result.drivers]
    assert driver_keys[0] == "engagement"
    assert driver_keys[1] == "manager_effectiveness"


def test_high_risk_stagnant_strong_performer_triggers_recognition_gap():
    # promotion: 72 months since last promotion -> saturates past the
    #   60-month ceiling -> risk 100
    # compensation: ratio 900,000/1,200,000 = 0.75 -> at/below the 0.85
    #   floor -> position risk 100; last raised 48 months ago, has a date so
    #   ceiling is 36 -> saturates -> momentum risk 100 -> avg 100
    # engagement 40 -> risk 60
    # manager effectiveness 50 -> risk 50 (present, but ranks below the top 4)
    # performance 4.3 >= 4.0 AND promotion/comp risk >= 50 -> gap triggers -> risk 100
    # score = 100*0.30 + 100*0.25 + 60*0.22 + 50*0.15 + 100*0.08
    #       = 30 + 25 + 13.2 + 7.5 + 8 = 83.7
    inputs = ScoringInputs(
        as_of=AS_OF,
        date_of_joining=dt.date(2015, 1, 1),
        grade="L4",
        last_promotion_date=dt.date(2020, 9, 21),
        last_increment_date=dt.date(2022, 9, 21),
        ctc_annual=900_000,
        peer_median_ctc_at_grade=1_200_000,
        peer_group_size=4,
        performance_rating=4.3,
        engagement_score=40,
        manager_effectiveness_score=50,
    )
    result = score_employee(inputs)
    assert result.score == pytest.approx(83.7, abs=0.05)
    assert result.band == RiskBand.CRITICAL
    driver_keys = {d.key for d in result.drivers}
    assert "performance_recognition_gap" in driver_keys
    gap_driver = next(d for d in result.drivers if d.key == "performance_recognition_gap")
    assert gap_driver.risk_points == 100.0
    # manager_effectiveness has the smallest weighted contribution of the
    # five factors here and should not crowd out the top 4.
    assert "manager_effectiveness" not in driver_keys


def test_missing_engagement_and_manager_data_renormalizes_weights():
    # Never promoted -> anchor is date_of_joining, ~44.65 months prior ->
    #   between the 18/60 ramp -> risk = (44.65-18)/42*100 = 63.4514...
    # Never incremented -> same anchor/months; position risk uses ratio
    #   3,000,000/3,000,000=1.0 -> inverse_linear_risk(1.0,0.85,1.05)=25.0;
    #   momentum uses the never-incremented ceiling of 24 -> saturates at
    #   100 -> avg (25+100)/2 = 62.5
    # engagement/manager_effectiveness/performance all None -> excluded,
    #   active weight = 0.30+0.25=0.55 -> data_completeness 0.55
    # score = (63.4514*0.30 + 62.5*0.25) / 0.55 = (19.0354+15.625)/0.55 = 63.0
    inputs = ScoringInputs(
        as_of=AS_OF,
        date_of_joining=dt.date(2023, 1, 1),
        grade="L5",
        last_promotion_date=None,
        last_increment_date=None,
        ctc_annual=3_000_000,
        peer_median_ctc_at_grade=3_000_000,
        peer_group_size=3,
        performance_rating=None,
        engagement_score=None,
        manager_effectiveness_score=None,
    )
    result = score_employee(inputs)
    assert result.score == pytest.approx(63.0, abs=0.1)
    assert result.band == RiskBand.HIGH
    assert result.data_completeness == pytest.approx(0.55)
    driver_keys = {d.key for d in result.drivers}
    assert driver_keys == {"promotion_stagnation", "compensation_trajectory"}


def test_small_peer_group_skips_position_comparison():
    # peer_group_size=1 is below the size-2 floor, so compensation risk
    # falls back to momentum only: last raised ~32.66 months ago, has a
    # date so ceiling is 36 -> risk = (32.66-12)/24*100 = 86.07...
    inputs = ScoringInputs(
        as_of=AS_OF,
        date_of_joining=dt.date(2018, 1, 1),
        grade="L6",
        last_promotion_date=dt.date(2023, 1, 1),
        last_increment_date=dt.date(2024, 1, 1),
        ctc_annual=3_800_000,
        peer_median_ctc_at_grade=3_800_000,
        peer_group_size=1,
        performance_rating=4.5,
        engagement_score=70,
        manager_effectiveness_score=70,
    )
    result = score_employee(inputs)
    comp_driver = next(d for d in result.drivers if d.key == "compensation_trajectory")
    assert comp_driver.risk_points == pytest.approx(86.07, abs=0.05)
    assert "peer group too small" in comp_driver.explanation


@pytest.mark.parametrize(
    "score,expected_band",
    [(0.0, RiskBand.LOW), (34.9, RiskBand.LOW), (35.0, RiskBand.MEDIUM), (59.9, RiskBand.MEDIUM), (60.0, RiskBand.HIGH), (79.9, RiskBand.HIGH), (80.0, RiskBand.CRITICAL), (100.0, RiskBand.CRITICAL)],
)
def test_risk_band_boundaries(score, expected_band):
    from app.scoring.model import _band_for_score

    assert _band_for_score(score) == expected_band


def test_driver_breakdown_always_has_at_least_two_drivers():
    inputs = ScoringInputs(
        as_of=AS_OF,
        date_of_joining=dt.date(2024, 1, 1),
        grade="L1",
        last_promotion_date=None,
        last_increment_date=None,
        ctc_annual=None,
        peer_median_ctc_at_grade=None,
        peer_group_size=0,
        performance_rating=None,
        engagement_score=None,
        manager_effectiveness_score=None,
    )
    result = score_employee(inputs)
    assert len(result.drivers) >= 2
    assert result.data_completeness == pytest.approx(0.55)  # only the two always-present factors


def test_no_usable_data_returns_neutral_flagged_score():
    inputs = ScoringInputs(
        as_of=AS_OF,
        date_of_joining=AS_OF,  # joined today: 0 months -> promotion risk 0, comp momentum risk 0
        grade="L1",
        last_promotion_date=None,
        last_increment_date=None,
        ctc_annual=None,
        peer_median_ctc_at_grade=None,
        peer_group_size=0,
        performance_rating=None,
        engagement_score=None,
        manager_effectiveness_score=None,
    )
    result = score_employee(inputs)
    # promotion_stagnation and compensation_trajectory are always computable
    # (they fall back to date_of_joining), so this is 0, not the fully
    # degenerate 50.0/data_completeness=0.0 path.
    assert result.score == pytest.approx(0.0)
    assert result.data_completeness == pytest.approx(0.55)
