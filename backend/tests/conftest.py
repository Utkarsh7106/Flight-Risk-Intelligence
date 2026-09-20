from __future__ import annotations

import datetime as dt
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.main import app
from app.models.business_unit import BusinessUnit
from app.models.department import Department
from app.models.employee import Employee

HR_EMAIL = "priya.sharma@lsdigital-demo.com"
HR_PASSWORD = "ChangeMe123!"
BU_HEAD_EMAIL = "arjun.mehta@lsdigital-demo.com"
BU_HEAD_PASSWORD = "ChangeMe123!"
BU_HEAD_BU_NAME = "Data Quark"
OTHER_BU_NAME = "Business Function and Media"


@pytest.fixture(scope="session")
def migrator_engine():
    url = settings.migrations_database_url or settings.database_url
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture()
def migrator_session(migrator_engine) -> Generator[Session, None, None]:
    with Session(migrator_engine) as session:
        yield session


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def _login(test_client: TestClient, email: str, password: str) -> TestClient:
    resp = test_client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return test_client


@pytest.fixture()
def hr_client(client: TestClient) -> TestClient:
    return _login(client, HR_EMAIL, HR_PASSWORD)


@pytest.fixture()
def bu_head_client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield _login(c, BU_HEAD_EMAIL, BU_HEAD_PASSWORD)


@pytest.fixture()
def seeded_employees(migrator_session: Session) -> Generator[dict, None, None]:
    """Seeds 3 employees across 2 BUs, including one whose manager sits in
    a different BU (for the manager-null-across-BU test). Written and torn
    down as fri_migrator, which bypasses RLS by table ownership — same
    pattern scripts/seed_reference_data.py uses for reference data.

    business_unit_id is deliberately left unset on each insert: the
    sync_employee_business_unit BEFORE INSERT trigger (migration
    5c6bf1a73a67) derives it from department_id, and this fixture exists
    partly to keep that trigger under test coverage too.
    """
    bu_head_bu = migrator_session.scalar(select(BusinessUnit).where(BusinessUnit.name == BU_HEAD_BU_NAME))
    other_bu = migrator_session.scalar(select(BusinessUnit).where(BusinessUnit.name == OTHER_BU_NAME))
    assert bu_head_bu is not None and other_bu is not None, (
        "seed data missing — run: cd backend && .venv/Scripts/python.exe scripts/seed_reference_data.py"
    )

    dept_in_bu_head_bu = migrator_session.scalar(
        select(Department).where(Department.business_unit_id == bu_head_bu.id)
    )
    dept_in_other_bu = migrator_session.scalar(
        select(Department).where(Department.business_unit_id == other_bu.id)
    )

    manager_in_other_bu = Employee(
        employee_code="TST-MGR1",
        full_name="Manager In Other BU",
        date_of_joining=dt.date(2020, 1, 1),
        department_id=dept_in_other_bu.id,
        grade="L5",
        email="tst.manager1@lsdigital-demo.com",
    )
    migrator_session.add(manager_in_other_bu)
    migrator_session.flush()

    own_employee = Employee(
        employee_code="TST-OWN1",
        full_name="Own BU Employee",
        date_of_joining=dt.date(2022, 6, 1),
        department_id=dept_in_bu_head_bu.id,
        grade="L3",
        email="tst.own1@lsdigital-demo.com",
        manager_id=manager_in_other_bu.id,
        ctc_annual=1500000,
        performance_rating=4.1,
    )
    other_employee = Employee(
        employee_code="TST-OTH1",
        full_name="Other BU Employee",
        date_of_joining=dt.date(2021, 3, 15),
        department_id=dept_in_other_bu.id,
        grade="L4",
        email="tst.oth1@lsdigital-demo.com",
        ctc_annual=2200000,
        performance_rating=3.6,
    )
    migrator_session.add_all([own_employee, other_employee])
    migrator_session.commit()

    data = {
        "bu_head_bu_id": bu_head_bu.id,
        "other_bu_id": other_bu.id,
        "own_employee_id": own_employee.id,
        "other_employee_id": other_employee.id,
        "manager_in_other_bu_id": manager_in_other_bu.id,
    }

    yield data

    migrator_session.execute(
        delete(Employee).where(
            Employee.id.in_([own_employee.id, other_employee.id, manager_in_other_bu.id])
        )
    )
    migrator_session.commit()
