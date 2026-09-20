from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.business_unit import BusinessUnit
from app.models.employee import Employee


def test_all_bu_head_accounts_authenticate_with_correct_role_and_bu(
    all_bu_head_clients: dict[str, TestClient],
):
    for bu_name, client in all_bu_head_clients.items():
        resp = client.get("/auth/me")
        assert resp.status_code == 200, f"{bu_name}: {resp.text}"
        body = resp.json()
        assert body["role"] == "bu_head"
        assert body["business_unit_id"] is not None


def test_each_bu_head_sees_only_their_own_bu_through_real_http(
    all_bu_head_clients: dict[str, TestClient], migrator_session: Session
):
    for bu_name, client in all_bu_head_clients.items():
        ground_truth = migrator_session.scalar(
            select(func.count())
            .select_from(Employee)
            .join(BusinessUnit, BusinessUnit.id == Employee.business_unit_id)
            .where(BusinessUnit.name == bu_name)
        )

        resp = client.get("/employees", params={"limit": 200})
        assert resp.status_code == 200
        body = resp.json()

        assert body["total"] == ground_truth, f"{bu_name}: expected {ground_truth}, got {body['total']}"
        for item in body["items"]:
            assert item["business_unit"]["name"] == bu_name, (
                f"{bu_name} login saw a row from {item['business_unit']['name']}"
            )


def test_no_bu_head_can_reach_another_bus_employee_by_id(
    all_bu_head_clients: dict[str, TestClient], one_employee_id_per_bu: dict[str, int]
):
    for viewer_bu, client in all_bu_head_clients.items():
        for owner_bu, employee_id in one_employee_id_per_bu.items():
            resp = client.get(f"/employees/{employee_id}")
            if owner_bu == viewer_bu:
                assert resp.status_code == 200, f"{viewer_bu} should see its own employee {employee_id}"
            else:
                assert resp.status_code == 404, (
                    f"{viewer_bu} login reached {owner_bu}'s employee {employee_id} (status {resp.status_code})"
                )
