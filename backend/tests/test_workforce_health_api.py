"""Module 2 Part 5: RLS-scoped access on score endpoints + the HR-only
fairness-audit gate, mirroring the existing directory isolation tests
(test_employees.py, test_bu_head_accounts.py) through the real HTTP path.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_hr_summary_spans_multiple_business_units(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.get("/workforce-health/summary")
    assert resp.status_code == 200
    body = resp.json()
    bu_ids = {bu["business_unit_id"] for bu in body["business_units"]}
    assert seeded_employees["bu_head_bu_id"] in bu_ids
    assert seeded_employees["other_bu_id"] in bu_ids


def test_bu_head_summary_scoped_to_own_bu_only(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get("/workforce-health/summary")
    assert resp.status_code == 200
    body = resp.json()
    bu_ids = {bu["business_unit_id"] for bu in body["business_units"]}
    assert bu_ids == {seeded_employees["bu_head_bu_id"]}


def test_bu_head_gets_own_bu_employee_score(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get(f"/workforce-health/employees/{seeded_employees['own_employee_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["employee_id"] == seeded_employees["own_employee_id"]
    assert 0.0 <= body["score"] <= 100.0
    assert len(body["drivers"]) >= 2
    assert len(body["recommendations"]) >= 1


def test_bu_head_cannot_reach_other_bu_employee_score(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get(f"/workforce-health/employees/{seeded_employees['other_employee_id']}")
    assert resp.status_code == 404


def test_hr_can_reach_any_employee_score(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.get(f"/workforce-health/employees/{seeded_employees['other_employee_id']}")
    assert resp.status_code == 200
    assert resp.json()["employee_id"] == seeded_employees["other_employee_id"]


def test_no_bu_head_can_reach_another_bus_employee_score(
    all_bu_head_clients: dict[str, TestClient], one_employee_id_per_bu: dict[str, int]
):
    for viewer_bu, client in all_bu_head_clients.items():
        for owner_bu, employee_id in one_employee_id_per_bu.items():
            resp = client.get(f"/workforce-health/employees/{employee_id}")
            if owner_bu == viewer_bu:
                assert resp.status_code == 200, f"{viewer_bu} should see its own employee's score"
            else:
                assert resp.status_code == 404, (
                    f"{viewer_bu} login reached {owner_bu}'s employee score (status {resp.status_code})"
                )


def test_hr_can_access_fairness_audit(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.get("/workforce-health/fairness-audit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_n"] > 0
    attributes = {a["attribute"] for a in body["attribute_audits"]}
    assert attributes == {"gender", "business_unit", "department", "location"}


def test_bu_head_is_refused_fairness_audit(bu_head_client: TestClient):
    resp = bu_head_client.get("/workforce-health/fairness-audit")
    assert resp.status_code == 403


def test_no_bu_head_account_can_reach_fairness_audit(all_bu_head_clients: dict[str, TestClient]):
    # Adversarial verification per MODULE2_REFERENCE.md: every seeded BU
    # Head login, not just one, must be refused — this is a
    # non-negotiable access control, so a single passing case isn't enough.
    for bu_name, client in all_bu_head_clients.items():
        resp = client.get("/workforce-health/fairness-audit")
        assert resp.status_code == 403, f"{bu_name} login reached the fairness audit (status {resp.status_code})"


def test_unauthenticated_request_refused_everywhere(client: TestClient):
    assert client.get("/workforce-health/summary").status_code == 401
    assert client.get("/workforce-health/employees/1").status_code == 401
    assert client.get("/workforce-health/fairness-audit").status_code == 401
