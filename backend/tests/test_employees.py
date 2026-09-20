from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.models.employee import Employee


def test_hr_sees_employees_across_multiple_bus(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.get("/employees", params={"limit": 200})
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()["items"]}
    assert seeded_employees["own_employee_id"] in ids
    assert seeded_employees["other_employee_id"] in ids


def test_bu_head_sees_only_own_bu(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get("/employees", params={"limit": 200})
    assert resp.status_code == 200
    body = resp.json()
    ids = {item["id"] for item in body["items"]}
    assert seeded_employees["own_employee_id"] in ids
    assert seeded_employees["other_employee_id"] not in ids
    assert seeded_employees["manager_in_other_bu_id"] not in ids
    for item in body["items"]:
        assert item["business_unit"]["id"] == seeded_employees["bu_head_bu_id"]


def test_bu_head_get_other_bu_employee_by_id_is_404(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get(f"/employees/{seeded_employees['other_employee_id']}")
    assert resp.status_code == 404


def test_bu_head_get_own_bu_employee_by_id_succeeds(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get(f"/employees/{seeded_employees['own_employee_id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == seeded_employees["own_employee_id"]


def test_bu_head_filter_by_other_business_unit_id_returns_empty(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get(
        "/employees", params={"business_unit_id": seeded_employees["other_bu_id"], "limit": 200}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_compensation_fields_are_row_scoped_not_flatly_returned(
    hr_client: TestClient, bu_head_client: TestClient, seeded_employees: dict
):
    hr_resp = hr_client.get(f"/employees/{seeded_employees['other_employee_id']}")
    assert hr_resp.status_code == 200
    assert hr_resp.json()["ctc_annual"] is not None

    bu_resp = bu_head_client.get(f"/employees/{seeded_employees['other_employee_id']}")
    assert bu_resp.status_code == 404

    own_resp = bu_head_client.get(f"/employees/{seeded_employees['own_employee_id']}")
    assert own_resp.status_code == 200
    assert own_resp.json()["ctc_annual"] is not None


def test_gender_never_appears_in_response(hr_client: TestClient, seeded_employees: dict):
    list_resp = hr_client.get("/employees", params={"limit": 200})
    for item in list_resp.json()["items"]:
        assert "gender" not in item

    detail = hr_client.get(f"/employees/{seeded_employees['own_employee_id']}").json()
    assert "gender" not in detail
    assert "date_of_birth" not in detail
    assert "phone" not in detail


def test_manager_in_different_bu_is_null_not_leaked(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get(f"/employees/{seeded_employees['own_employee_id']}")
    assert resp.status_code == 200
    assert resp.json()["manager"] is None


def test_missing_rls_context_returns_empty_not_error(seeded_employees: dict):
    """No SET LOCAL app.current_role/app.current_bu_id is ever issued on
    this connection. Must return zero rows, not raise — the named test for
    the 'fails closed but silently' tradeoff of leaving all filtering to
    RLS (design spec, 'Enforcement boundary'). seeded_employees proves
    rows genuinely exist while this still returns none.
    """
    with SessionLocal() as db:
        rows = db.scalars(select(Employee)).all()
        assert rows == []


def test_sort_by_disallowed_value_is_rejected_before_query(hr_client: TestClient):
    resp = hr_client.get("/employees", params={"sort_by": "password_hash"})
    assert resp.status_code == 422


def test_sort_by_each_allowed_value_succeeds(hr_client: TestClient, seeded_employees: dict):
    for column in [
        "full_name", "employee_code", "date_of_joining", "grade",
        "designation", "location", "ctc_annual", "performance_rating",
    ]:
        resp = hr_client.get("/employees", params={"sort_by": column, "limit": 200})
        assert resp.status_code == 200, f"sort_by={column} failed: {resp.text}"
