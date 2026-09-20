"""Module 2 Part 5: fairness/proxy-leakage audit statistics.

Pure-function tests against app/scoring/fairness_audit.py — no DB, no
HTTP. The HR-only access gate itself is tested in
test_workforce_health_api.py (adversarial: confirm a BU Head is refused).
"""

from __future__ import annotations

from app.scoring.fairness_audit import EmployeeScoreForAudit, build_fairness_audit


def _emp(
    employee_id: int,
    score: float,
    gender: str | None = "Female",
    bu: str = "Data Quark",
    dept: str = "Digital Analytics",
    location: str | None = "Mumbai",
    manager_id: int | None = None,
    manager_name: str | None = None,
) -> EmployeeScoreForAudit:
    return EmployeeScoreForAudit(
        employee_id=employee_id,
        score=score,
        gender=gender,
        business_unit_name=bu,
        department_name=dept,
        location=location,
        manager_id=manager_id,
        manager_name=manager_name,
    )


def test_large_gap_in_a_large_enough_group_is_flagged():
    scores = (
        [_emp(i, 20.0, gender="Male") for i in range(10)]
        + [_emp(100 + i, 60.0, gender="Female") for i in range(10)]
    )
    result = build_fairness_audit(scores)
    gender_audit = next(a for a in result.attribute_audits if a.attribute == "gender")
    female_group = next(g for g in gender_audit.groups if g.group_value == "Female")
    male_group = next(g for g in gender_audit.groups if g.group_value == "Male")
    assert female_group.flagged is True
    assert male_group.flagged is True
    assert female_group.confidence == "higher"
    assert female_group.mean_score == 60.0
    assert female_group.gap_from_overall == 20.0  # overall mean is (20*10+60*10)/20 = 40


def test_small_group_never_flagged_even_with_a_huge_gap():
    scores = [_emp(1, 5.0, location="Pune"), _emp(2, 95.0, location="Bengaluru")] + [
        _emp(10 + i, 50.0, location="Bengaluru") for i in range(4)
    ]
    result = build_fairness_audit(scores)
    location_audit = next(a for a in result.attribute_audits if a.attribute == "location")
    pune_group = next(g for g in location_audit.groups if g.group_value == "Pune")
    assert pune_group.n == 1
    assert pune_group.confidence == "insufficient_data"
    assert pune_group.flagged is False


def test_missing_attribute_values_excluded_and_counted():
    scores = [
        _emp(1, 50.0, location="Mumbai"),
        _emp(2, 50.0, location=None),
        _emp(3, 50.0, location=None),
        _emp(4, 50.0, location="Mumbai"),
    ]
    result = build_fairness_audit(scores)
    location_audit = next(a for a in result.attribute_audits if a.attribute == "location")
    assert location_audit.excluded_missing_data == 2
    assert sum(g.n for g in location_audit.groups) == 2


def test_manager_with_elevated_team_score_is_flagged():
    scores = [_emp(i, 30.0, manager_id=1, manager_name="Rohan Kapoor") for i in range(3)] + [
        _emp(10 + i, 75.0, manager_id=2, manager_name="Anjali Verma") for i in range(3)
    ] + [_emp(20 + i, 45.0, manager_id=None) for i in range(4)]  # unmanaged, excluded from manager audit
    result = build_fairness_audit(scores)
    manager_ids = {m.manager_id: m for m in result.manager_audits}
    assert manager_ids[2].flagged is True
    assert manager_ids[2].manager_name == "Anjali Verma"
    assert manager_ids[1].flagged is False


def test_manager_team_below_min_size_excluded_entirely():
    scores = [_emp(1, 95.0, manager_id=7, manager_name="Solo Manager")] + [
        _emp(10 + i, 40.0, manager_id=2, manager_name="Team Manager") for i in range(3)
    ]
    result = build_fairness_audit(scores)
    manager_ids = {m.manager_id for m in result.manager_audits}
    assert 7 not in manager_ids
    assert 2 in manager_ids


def test_empty_input_returns_zeroed_result_without_error():
    result = build_fairness_audit([])
    assert result.overall_n == 0
    assert result.overall_mean_score == 0.0
    assert result.attribute_audits == []
    assert result.manager_audits == []


def test_no_flag_when_gap_below_threshold():
    scores = [_emp(i, 50.0, gender="Male") for i in range(10)] + [
        _emp(100 + i, 55.0, gender="Female") for i in range(10)
    ]
    result = build_fairness_audit(scores)
    gender_audit = next(a for a in result.attribute_audits if a.attribute == "gender")
    for group in gender_audit.groups:
        assert group.flagged is False
