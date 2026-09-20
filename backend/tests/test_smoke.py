from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_hr_login_fixture_works(hr_client: TestClient):
    resp = hr_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "hr"


def test_bu_head_login_fixture_works(bu_head_client: TestClient):
    resp = bu_head_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "bu_head"


def test_seeded_employees_fixture_creates_and_tears_down(seeded_employees: dict, migrator_session):
    from sqlalchemy import select

    from app.models.employee import Employee

    assert migrator_session.scalar(
        select(Employee).where(Employee.id == seeded_employees["own_employee_id"])
    ) is not None
