"""Module 3: RLS-scoped access on /risk-analysis/*, mirroring the exact
pattern already proven for /employees and /workforce-health (see
test_employees.py, test_workforce_health_api.py). No fairness-audit
endpoint exists in this module — that stays Module 2's, over real
scoring inputs.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_hr_summary_spans_multiple_business_units(hr_client: TestClient, seeded_synthetic_employees: dict):
    resp = hr_client.get("/risk-analysis/summary")
    assert resp.status_code == 200
    body = resp.json()
    bu_ids = {bu["business_unit_id"] for bu in body["business_units"]}
    assert seeded_synthetic_employees["bu_head_bu_id"] in bu_ids
    assert seeded_synthetic_employees["other_bu_id"] in bu_ids


def test_bu_head_summary_scoped_to_own_bu_only(bu_head_client: TestClient, seeded_synthetic_employees: dict):
    resp = bu_head_client.get("/risk-analysis/summary")
    assert resp.status_code == 200
    body = resp.json()
    bu_ids = {bu["business_unit_id"] for bu in body["business_units"]}
    assert bu_ids == {seeded_synthetic_employees["bu_head_bu_id"]}


def test_bu_head_gets_own_bu_employee_detail(bu_head_client: TestClient, seeded_synthetic_employees: dict):
    resp = bu_head_client.get(f"/risk-analysis/employees/{seeded_synthetic_employees['own_employee_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == seeded_synthetic_employees["own_employee_id"]
    assert 0.0 <= body["predicted_probability"] <= 1.0
    assert body["risk_band"] in ("low", "medium", "high", "critical")
    assert len(body["drivers"]) >= 1


def test_bu_head_cannot_reach_other_bu_employee(bu_head_client: TestClient, seeded_synthetic_employees: dict):
    resp = bu_head_client.get(f"/risk-analysis/employees/{seeded_synthetic_employees['other_employee_id']}")
    assert resp.status_code == 404


def test_hr_can_reach_any_employee(hr_client: TestClient, seeded_synthetic_employees: dict):
    resp = hr_client.get(f"/risk-analysis/employees/{seeded_synthetic_employees['other_employee_id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == seeded_synthetic_employees["other_employee_id"]


def test_no_bu_head_can_reach_another_bus_employee(
    all_bu_head_clients: dict[str, TestClient], seeded_synthetic_employees: dict
):
    own_id = seeded_synthetic_employees["own_employee_id"]
    for bu_name, client in all_bu_head_clients.items():
        resp = client.get(f"/risk-analysis/employees/{own_id}")
        if bu_name == "Data Quark":
            assert resp.status_code == 200, f"{bu_name} should see its own seeded employee"
        else:
            assert resp.status_code == 404, f"{bu_name} login reached another BU's employee (status {resp.status_code})"


def test_separated_employee_never_reachable_even_by_hr(hr_client: TestClient, seeded_synthetic_employees: dict):
    # 'separated' rows are labeled training examples only (see
    # app/synthetic/generate.py) — never served through this API, for
    # any role.
    resp = hr_client.get(f"/risk-analysis/employees/{seeded_synthetic_employees['separated_employee_id']}")
    assert resp.status_code == 404


def test_employees_list_excludes_separated_rows(hr_client: TestClient, seeded_synthetic_employees: dict):
    resp = hr_client.get("/risk-analysis/employees", params={"limit": 200})
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()["items"]}
    assert seeded_synthetic_employees["separated_employee_id"] not in ids
    assert seeded_synthetic_employees["own_employee_id"] in ids


def test_sort_by_disallowed_value_is_rejected_before_query(hr_client: TestClient):
    resp = hr_client.get("/risk-analysis/employees", params={"sort_by": "predicted_probability; DROP TABLE synthetic_employee;"})
    assert resp.status_code == 422


def test_unauthenticated_request_refused_everywhere(client: TestClient):
    assert client.get("/risk-analysis/summary").status_code == 401
    assert client.get("/risk-analysis/employees").status_code == 401
    assert client.get("/risk-analysis/employees/1").status_code == 401
