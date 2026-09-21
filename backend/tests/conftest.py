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
from app.models.synthetic_employee import SyntheticEmployee

HR_EMAIL = "priya.sharma@lsdigital-demo.com"
HR_PASSWORD = "ChangeMe123!"
BU_HEAD_EMAIL = "arjun.mehta@lsdigital-demo.com"
BU_HEAD_PASSWORD = "ChangeMe123!"
BU_HEAD_BU_NAME = "Data Quark"
OTHER_BU_NAME = "Business Function and Media"

# One bu_head login per business unit — mirrors scripts/seed_reference_data.py's
# TEST_ACCOUNTS exactly. Every BU is logged into for real over HTTP in
# test_bu_head_accounts.py; there's no direct-RLS-session stand-in left.
ALL_BU_HEADS: dict[str, tuple[str, str]] = {
    "Data Quark": (BU_HEAD_EMAIL, BU_HEAD_PASSWORD),
    "Business Function and Media": ("meenakshi.reddy@lsdigital-demo.com", "ChangeMe123!"),
    "Enabling Functions": ("siddharth.agarwal@lsdigital-demo.com", "ChangeMe123!"),
    "SP Creative": ("pooja.bhattacharya@lsdigital-demo.com", "ChangeMe123!"),
    "UI/UX": ("aditya.choudhary@lsdigital-demo.com", "ChangeMe123!"),
}


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
def all_bu_head_clients() -> Generator[dict[str, TestClient], None, None]:
    """One logged-in TestClient per business unit, each its own instance
    so the 5 cookie sessions never collide. Used to prove BU isolation
    holds for every BU through a real HTTP login, not a subset.
    """
    with TestClient(app) as c1, TestClient(app) as c2, TestClient(app) as c3, \
         TestClient(app) as c4, TestClient(app) as c5:
        clients = [c1, c2, c3, c4, c5]
        yield {
            bu_name: _login(client, email, password)
            for client, (bu_name, (email, password)) in zip(clients, ALL_BU_HEADS.items())
        }


@pytest.fixture()
def one_employee_id_per_bu(migrator_session: Session) -> dict[str, int]:
    """Ground truth for the all-5-BUs isolation test: one real employee id
    per BU, read live from whatever's actually seeded (the illustrative
    batch from scripts/seed_reference_data.py), not hardcoded ids. Asserts
    all 5 BUs are represented so a missing seed fails loudly instead of
    letting the isolation test pass vacuously on empty data.
    """
    rows = migrator_session.execute(
        select(BusinessUnit.name, Employee.id).join(Employee, Employee.business_unit_id == BusinessUnit.id)
    ).all()
    result: dict[str, int] = {}
    for bu_name, employee_id in rows:
        result.setdefault(bu_name, employee_id)
    assert set(result) == set(ALL_BU_HEADS), (
        "expected illustrative seed employees in all 5 BUs — run: "
        "cd backend && .venv/Scripts/python.exe scripts/seed_reference_data.py"
    )
    return result


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


@pytest.fixture()
def seeded_synthetic_employees(migrator_session: Session) -> Generator[dict, None, None]:
    """Small, self-contained Module 3 fixture — deliberately independent of
    the full ~3000-row generated dataset (app/synthetic/generate.py +
    train.py), which needs requirements-ml.txt and several seconds to
    produce and isn't assumed to exist wherever this suite runs. Mirrors
    seeded_employees' shape: one active row in the BU-head's own BU, one
    active row in another BU (for the cross-BU isolation test), and one
    'separated' row (a labeled training example, never API-visible) to
    prove that exclusion holds even for HR.
    """
    bu_head_bu = migrator_session.scalar(select(BusinessUnit).where(BusinessUnit.name == BU_HEAD_BU_NAME))
    other_bu = migrator_session.scalar(select(BusinessUnit).where(BusinessUnit.name == OTHER_BU_NAME))
    dept_in_bu_head_bu = migrator_session.scalar(
        select(Department).where(Department.business_unit_id == bu_head_bu.id)
    )
    dept_in_other_bu = migrator_session.scalar(
        select(Department).where(Department.business_unit_id == other_bu.id)
    )

    sample_drivers = [
        {
            "feature": "overtime",
            "label": "Frequent overtime",
            "value": 1.0,
            "shap_value": 0.18,
            "explanation": "Frequent overtime (frequent overtime) increased predicted risk",
        }
    ]

    common = dict(
        date_of_joining=dt.date(2021, 4, 1),
        grade="L3",
        ctc_annual=1_500_000,
        performance_rating=3.4,
        engagement_score=60.0,
        manager_effectiveness_score=60.0,
        overtime=True,
        job_satisfaction_score=55.0,
        distance_from_home_km=10.0,
        employment_status="active",
        predicted_probability=0.42,
        risk_band="high",
        shap_drivers=sample_drivers,
    )

    own_employee = SyntheticEmployee(
        employee_code="TST-SYN-OWN1", full_name="Synthetic Own BU", department_id=dept_in_bu_head_bu.id, **common
    )
    other_employee = SyntheticEmployee(
        employee_code="TST-SYN-OTH1", full_name="Synthetic Other BU", department_id=dept_in_other_bu.id, **common
    )
    separated_common = {**common, "employment_status": "separated", "predicted_probability": None, "risk_band": None, "shap_drivers": None}
    separated_employee = SyntheticEmployee(
        employee_code="TST-SYN-SEP1", full_name="Synthetic Separated", department_id=dept_in_bu_head_bu.id, **separated_common
    )
    migrator_session.add_all([own_employee, other_employee, separated_employee])
    migrator_session.commit()

    data = {
        "bu_head_bu_id": bu_head_bu.id,
        "other_bu_id": other_bu.id,
        "own_employee_id": own_employee.id,
        "other_employee_id": other_employee.id,
        "separated_employee_id": separated_employee.id,
    }

    yield data

    migrator_session.execute(
        delete(SyntheticEmployee).where(
            SyntheticEmployee.id.in_([own_employee.id, other_employee.id, separated_employee.id])
        )
    )
    migrator_session.commit()
