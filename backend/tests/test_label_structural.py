"""Module 3: proves the label generator structurally cannot read forbidden
attributes, and that its randomness genuinely varies outcomes — the two
properties MODULE3_REFERENCE.md calls out as what keeps this from being
Module 2's circularity mistake one level removed. Mirrors
test_scoring_structural.py's approach for Module 2.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import random

from app.models.employee import Employee
from app.synthetic.features import Features, RawSignals
from app.synthetic.label import departure_probability, draw_label

FORBIDDEN_FIELD_NAMES = {"gender", "business_unit_id", "department_id", "manager_id", "location"}


def test_raw_signals_has_no_forbidden_fields():
    field_names = {f.name for f in dataclasses.fields(RawSignals)}
    overlap = field_names & FORBIDDEN_FIELD_NAMES
    assert overlap == set(), f"RawSignals must never carry {FORBIDDEN_FIELD_NAMES} — found {overlap}."


def test_features_has_no_forbidden_fields():
    field_names = {f.name for f in dataclasses.fields(Features)}
    overlap = field_names & FORBIDDEN_FIELD_NAMES
    assert overlap == set(), f"Features must never carry {FORBIDDEN_FIELD_NAMES} — found {overlap}."


def test_forbidden_field_names_still_exist_on_employee_model():
    # Guards the guard, same as test_scoring_structural.py.
    employee_field_names = {c.key for c in Employee.__table__.columns}
    assert FORBIDDEN_FIELD_NAMES <= employee_field_names


def _sample_features(**overrides) -> Features:
    base = dict(
        tenure_years=3.0,
        months_since_promotion=20.0,
        months_since_increment=10.0,
        ctc_ratio_to_grade_median=1.0,
        performance_rating=3.2,
        engagement_score=65.0,
        manager_effectiveness_score=65.0,
        overtime=0.0,
        job_satisfaction_score=65.0,
        distance_from_home_km=10.0,
        grade_ordinal=3,
    )
    base.update(overrides)
    return Features(**base)


def test_identical_features_can_produce_different_outcomes_due_to_noise():
    # The single most important structural property from
    # MODULE3_REFERENCE.md: the label is NOT a deterministic function of
    # the features (unlike the original hackathon's approach). Same
    # features, many different noise draws, must show real variance in
    # the resulting probability.
    features = _sample_features()
    rng = random.Random(1)
    probabilities = {round(draw_label(features, intercept=-2.0, rng=rng).probability, 4) for _ in range(200)}
    assert len(probabilities) > 50, "expected substantial spread in probability across noise draws"


def test_identical_features_and_seed_are_reproducible():
    # Determinism given a fixed seed (needed for reproducible dataset
    # generation) is not in tension with per-draw randomness above — same
    # seed replayed from scratch must reproduce the same sequence.
    features = _sample_features()
    draws_a = [draw_label(features, intercept=-2.0, rng=random.Random(42)).left_company for _ in range(20)]
    draws_b = [draw_label(features, intercept=-2.0, rng=random.Random(42)).left_company for _ in range(20)]
    assert draws_a == draws_b


def test_overtime_raises_probability_directionally():
    # Sanity check on the generator's directional honesty — not a
    # tautology check against Module 2 (this module has no dependency on
    # app/scoring/model.py at all), just confirming the log-odds term
    # actually does what its comment in label.py claims.
    without_overtime = _sample_features(overtime=0.0)
    with_overtime = _sample_features(overtime=1.0)
    # No noise, so this isolates the deterministic term's effect.
    p_without = departure_probability(without_overtime, intercept=-2.0, noise=0.0)
    p_with = departure_probability(with_overtime, intercept=-2.0, noise=0.0)
    assert p_with > p_without


def test_departure_probability_signature_has_no_forbidden_keyword():
    import inspect

    sig = inspect.signature(departure_probability)
    assert set(sig.parameters.keys()) == {"features", "intercept", "noise"}
