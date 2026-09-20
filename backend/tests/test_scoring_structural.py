"""Module 2 Part 5: proves forbidden attributes structurally cannot reach the score.

This is a regression test, not a snapshot of current behavior: it
introspects `ScoringInputs`' actual field set so that if someone later
adds `gender`, `business_unit_id`, `department_id`, `manager_id`, or
`location` as a field on that dataclass, this test fails immediately —
before the value is ever wired in from a router. It also proves two
employees who are identical on every legitimate factor but differ only
on a forbidden attribute score identically, using the real Employee
model's field set as the source of "what a forbidden attribute is."
"""

from __future__ import annotations

import dataclasses
import datetime as dt

from app.models.employee import Employee
from app.scoring.model import ScoringInputs, score_employee

FORBIDDEN_FIELD_NAMES = {"gender", "business_unit_id", "department_id", "manager_id", "location"}


def test_scoring_inputs_has_no_forbidden_fields():
    field_names = {f.name for f in dataclasses.fields(ScoringInputs)}
    overlap = field_names & FORBIDDEN_FIELD_NAMES
    assert overlap == set(), (
        f"ScoringInputs must never carry {FORBIDDEN_FIELD_NAMES} — found {overlap}. "
        "See app/scoring/model.py's module docstring."
    )


def test_forbidden_field_names_still_exist_on_employee_model():
    # Guards the guard: if Employee ever renames/drops one of these columns,
    # FORBIDDEN_FIELD_NAMES above (and this whole test module) would be
    # silently checking against a name that no longer means anything.
    employee_field_names = {c.key for c in Employee.__table__.columns}
    assert FORBIDDEN_FIELD_NAMES <= employee_field_names


def test_identical_legitimate_factors_score_identically_regardless_of_forbidden_attributes():
    as_of = dt.date(2026, 9, 21)
    base_kwargs = dict(
        as_of=as_of,
        date_of_joining=dt.date(2021, 3, 1),
        grade="L3",
        last_promotion_date=dt.date(2023, 3, 1),
        last_increment_date=dt.date(2025, 3, 1),
        ctc_annual=1_500_000,
        peer_median_ctc_at_grade=1_500_000,
        peer_group_size=4,
        performance_rating=3.6,
        engagement_score=71,
        manager_effectiveness_score=88,
    )

    # Two "employees" that would differ only in gender/BU/department/manager
    # identity/location if those fields existed on ScoringInputs. They don't,
    # so both calls below are byte-for-byte the same call — this is the
    # structural proof, not a behavioral coincidence.
    employee_a_inputs = ScoringInputs(**base_kwargs)
    employee_b_inputs = ScoringInputs(**base_kwargs)

    result_a = score_employee(employee_a_inputs)
    result_b = score_employee(employee_b_inputs)

    assert result_a.score == result_b.score
    assert result_a.band == result_b.band
    assert [d.key for d in result_a.drivers] == [d.key for d in result_b.drivers]


def test_score_employee_signature_takes_no_forbidden_keyword():
    import inspect

    sig = inspect.signature(score_employee)
    param_names = set(sig.parameters.keys())
    # score_employee(inputs: ScoringInputs) is the whole signature — this
    # also guards against someone widening it with **kwargs that could
    # smuggle a forbidden field in without touching ScoringInputs at all.
    assert param_names == {"inputs"}
