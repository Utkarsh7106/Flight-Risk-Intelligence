# Employee Directory Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a role-scoped employee directory (`GET /employees`, `GET /employees/{id}`) enforced entirely by the existing Postgres RLS policies, with a pytest suite proving BU isolation through the real HTTP path, plus the 15-minute token change and doc sync agreed alongside it.

**Architecture:** Two new files (`app/schemas/employee.py`, `app/routers/employees.py`) added to the existing FastAPI app; router adds zero role-derived filtering of its own — `get_current_user`'s `_set_rls_context()` already sets `SET LOCAL app.current_role` / `app.current_bu_id` on the request's transaction (via `Depends(get_db)` caching the same `Session`), and the RLS policies from migration `5c6bf1a73a67` do the scoping. `sort_by` is a closed `Literal` type indexing a hardcoded dict — never `getattr()`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 Core `select()`, Pydantic v2 (`from_attributes`), pytest + `fastapi.testclient.TestClient` (sync, backed by `httpx`), real local Postgres (`fri_dev`) — no mocking of the DB or RLS layer.

## Global Constraints

- Router must never add `WHERE business_unit_id = ...` or any role-derived filter — RLS is the only enforcement layer (see design spec, "Enforcement boundary").
- `sort_by` must be a `Literal[...]` validated by Pydantic before any SQL is built, then index a hardcoded `dict[str, InstrumentedAttribute]` — never `getattr()` on a user string.
- Response schema must never include `gender`, `date_of_birth`, or `phone` (design spec, "Response fields").
- Detail endpoint returns 404, never 403, when RLS hides a row.
- `JWT_EXPIRE_MINUTES` changes from 30 to 15; both `ARCHITECTURE.md` locations and `.env.example` must agree with the new value.
- Tests run against the real local `fri_dev` database as `fri_app` (via the app's normal `.env`) and as `fri_migrator` (for fixture setup/teardown) — no SQLite, no mocked session.
- Every new/changed file uses the project's existing style: `from __future__ import annotations`, type hints on everything, no comments explaining *what* code does (only non-obvious *why*, matching the rest of the codebase).

---

### Task 1: Shorten JWT expiry to 15 minutes

**Files:**
- Modify: `backend/app/config.py:15` (`jwt_expire_minutes: int = 30` → `15`)
- Modify: `backend/.env.example` (`JWT_EXPIRE_MINUTES=30` → `15`)
- Test: `backend/tests/test_jwt.py` (new)

**Interfaces:**
- Consumes: `app.security.jwt.create_access_token(subject, role, business_unit_id) -> str` (existing, unchanged signature).
- Produces: nothing new consumed by later tasks — this is a leaf change.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/__init__.py` (empty file, makes `tests` a package):

```python
```

Create `backend/tests/test_jwt.py`:

```python
from __future__ import annotations

import datetime as dt

from app.config import settings
from app.security.jwt import create_access_token, decode_access_token


def test_jwt_expiry_is_fifteen_minutes():
    assert settings.jwt_expire_minutes == 15


def test_access_token_exp_claim_is_fifteen_minutes_from_iat():
    token = create_access_token(subject="1", role="hr", business_unit_id=None)
    payload = decode_access_token(token)
    delta = payload["exp"] - payload["iat"]
    assert delta == 15 * 60
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `.venv/Scripts/python.exe -m pytest tests/test_jwt.py -v`
Expected: `test_jwt_expiry_is_fifteen_minutes` FAILs — `assert 30 == 15`. (This requires `.env` to be present with valid `DATABASE_URL`/`JWT_SECRET`, since `Settings()` reads it at import; it already is, from local setup.)

- [ ] **Step 3: Make the change**

In `backend/app/config.py`, change:
```python
    jwt_expire_minutes: int = 30
```
to:
```python
    jwt_expire_minutes: int = 15
```

In `backend/.env.example`, change:
```
JWT_EXPIRE_MINUTES=30
```
to:
```
JWT_EXPIRE_MINUTES=15
```

In `backend/.env` (the real local file, gitignored — not the example), make the same change so the running app and tests actually pick up 15 minutes:
```
JWT_EXPIRE_MINUTES=15
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jwt.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/.env.example backend/tests/__init__.py backend/tests/test_jwt.py
git commit -m "Shorten JWT access token expiry from 30 to 15 minutes

Internal office use on potentially shared/unlocked machines — the
realistic risk is device access, not token interception in transit, so
a shorter window is the proportionate fix. Not building revocation."
```

(`.env` itself is gitignored and won't be staged — verify with `git status` that only the four files above are staged.)

---

### Task 2: Test scaffolding — dev dependencies, pytest config, DB/HTTP fixtures

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Test: this task's own deliverable IS the test infrastructure; verified by a trivial smoke test.

**Interfaces:**
- Produces (consumed by Task 4's test file):
  - fixture `client() -> TestClient` — unauthenticated.
  - fixture `hr_client(client) -> TestClient` — logged in as `priya.sharma@lsdigital-demo.com`.
  - fixture `bu_head_client() -> TestClient` — logged in as `arjun.mehta@lsdigital-demo.com`, own `TestClient` instance (not sharing cookies with `hr_client`).
  - fixture `migrator_session() -> Session` — connected as `fri_migrator`, bypasses RLS, for fixture setup/teardown.
  - fixture `seeded_employees() -> dict` with keys: `bu_head_bu_id`, `other_bu_id`, `own_employee_id`, `other_employee_id`, `manager_in_other_bu_id`.
  - constants `HR_EMAIL`, `HR_PASSWORD`, `BU_HEAD_EMAIL`, `BU_HEAD_PASSWORD`, `BU_HEAD_BU_NAME`, `OTHER_BU_NAME`.

- [ ] **Step 1: Install dev dependencies and capture exact versions**

Run (from `backend/`):
```bash
.venv/Scripts/python.exe -m pip install pytest httpx
.venv/Scripts/python.exe -m pip freeze | grep -iE "^(pytest|httpx|iniconfig|pluggy)="
```

Take the exact version strings from that output and write `backend/requirements-dev.txt`:

```
-r requirements.txt

# Testing (see backend/tests/ and backend/README.md)
pytest==<captured version>
httpx==<captured version>
```

(Use the literal versions pip just installed — do not guess. `iniconfig`/`pluggy` are pytest's own transitive deps and don't need pinning here.)

- [ ] **Step 2: Write pytest config**

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 3: Write conftest.py fixtures**

Create `backend/tests/conftest.py`:

```python
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
```

- [ ] **Step 4: Write and run a smoke test to verify the fixtures work end to end**

Create `backend/tests/test_smoke.py` (temporary — deleted in Task 4 once real tests exist):

```python
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
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v`
Expected: all 4 PASS. This proves login works, both accounts authenticate, and the fixture can write/read via `fri_migrator` before any router code exists to depend on it.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements-dev.txt backend/pytest.ini backend/tests/conftest.py backend/tests/test_smoke.py
git commit -m "Add pytest scaffolding: dev deps, fixtures for HR/BU Head login and seeded cross-BU employees"
```

---

### Task 3: Employee response schemas

**Files:**
- Create: `backend/app/schemas/employee.py`

**Interfaces:**
- Consumes: `app.models.employee.Employee` (existing — fields per the design spec's "Response fields" section).
- Produces: `EmployeeOut`, `EmployeeListResponse` — imported by Task 4's router as `from app.schemas.employee import EmployeeListResponse, EmployeeOut`.

- [ ] **Step 1: Write the schema**

Create `backend/app/schemas/employee.py`:

```python
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, computed_field


class DepartmentRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BusinessUnitRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ManagerRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class EmployeeOut(BaseModel):
    """Directory view — table and card layouts both read from this shape.

    Deliberately excludes gender, date_of_birth, and phone. gender is
    ARCHITECTURE.md-mandated (HR-only fairness-audit endpoint later, never
    the ordinary directory). date_of_birth is an age proxy, excluded in
    the same spirit. phone is contact PII with no role in a flight-risk
    view. Do not add any of the three here without updating
    ARCHITECTURE.md and docs/superpowers/specs/2026-09-20-employee-directory-endpoint-design.md.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    email: str
    avatar_url: str | None
    designation: str | None
    grade: str
    location: str | None
    employment_status: str
    date_of_joining: dt.date

    department: DepartmentRef
    business_unit: BusinessUnitRef
    manager: ManagerRef | None

    ctc_annual: float | None
    last_increment_date: dt.date | None
    last_increment_pct: float | None
    last_promotion_date: dt.date | None
    performance_rating: float | None
    engagement_score: float | None
    manager_effectiveness_score: float | None

    @computed_field
    @property
    def tenure_years(self) -> float:
        days = (dt.date.today() - self.date_of_joining).days
        return round(days / 365.25, 1)


class EmployeeListResponse(BaseModel):
    items: list[EmployeeOut]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 2: Verify it imports cleanly**

Run (from `backend/`): `.venv/Scripts/python.exe -c "from app.schemas.employee import EmployeeOut, EmployeeListResponse; print('ok')"`
Expected: `ok` (no import errors — this file has no router/DB dependency yet, so this is a fast sanity check, not a full test).

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/employee.py
git commit -m "Add employee directory response schemas

Excludes gender/date_of_birth/phone per ARCHITECTURE.md and the design
spec — table+card views share one shape via computed tenure_years."
```

---

### Task 4: Employee router, registration, and full RLS-through-HTTP test suite

**Files:**
- Create: `backend/app/routers/employees.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_employees.py`
- Delete: `backend/tests/test_smoke.py` (superseded — its coverage is subsumed by `test_employees.py`'s `hr_client`/`bu_head_client`/`seeded_employees` usage)

**Interfaces:**
- Consumes: `EmployeeOut`, `EmployeeListResponse` (Task 3); `get_current_user`, `get_db` (existing, `app/security/deps.py` / `app/database.py`); fixtures from Task 2's `conftest.py`.
- Produces: `GET /employees`, `GET /employees/{employee_id}` — terminal for this plan, nothing downstream depends on these beyond the frontend (out of scope).

- [ ] **Step 1: Write the failing tests first**

Create `backend/tests/test_employees.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_employees.py -v`
Expected: every test FAILs with 404 on `/employees` (route doesn't exist yet) — confirms the tests are exercising real behavior, not vacuously passing.

- [ ] **Step 3: Write the router**

Create `backend/app/routers/employees.py`:

```python
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.database import get_db
from app.models.app_user import AppUser
from app.models.employee import Employee
from app.schemas.employee import EmployeeListResponse, EmployeeOut
from app.security.deps import get_current_user

router = APIRouter(prefix="/employees", tags=["employees"])

# Hardcoded allow-list: sort_by only ever indexes into this dict, never
# getattr() on a user-supplied string. SortBy (below) also constrains the
# incoming value to this same set before it ever reaches this dict, so an
# invalid column is rejected by FastAPI/Pydantic (422) before any SQL is
# built. See ARCHITECTURE.md security guardrails.
SORT_COLUMNS: dict[str, InstrumentedAttribute] = {
    "full_name": Employee.full_name,
    "employee_code": Employee.employee_code,
    "date_of_joining": Employee.date_of_joining,
    "grade": Employee.grade,
    "designation": Employee.designation,
    "location": Employee.location,
    "ctc_annual": Employee.ctc_annual,
    "performance_rating": Employee.performance_rating,
}

SortBy = Literal[
    "full_name", "employee_code", "date_of_joining", "grade",
    "designation", "location", "ctc_annual", "performance_rating",
]


def _apply_filters(
    stmt: Select,
    *,
    business_unit_id: int | None,
    department_id: int | None,
    grade: str | None,
    employment_status: str | None,
    location: str | None,
    q: str | None,
) -> Select:
    if business_unit_id is not None:
        stmt = stmt.where(Employee.business_unit_id == business_unit_id)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if grade is not None:
        stmt = stmt.where(Employee.grade == grade)
    if employment_status is not None:
        stmt = stmt.where(Employee.employment_status == employment_status)
    if location is not None:
        stmt = stmt.where(Employee.location == location)
    if q is not None:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Employee.full_name.ilike(pattern)
            | Employee.employee_code.ilike(pattern)
            | Employee.designation.ilike(pattern)
        )
    return stmt


def _with_relations(stmt: Select) -> Select:
    return stmt.options(
        selectinload(Employee.department),
        selectinload(Employee.business_unit),
        selectinload(Employee.manager),
    )


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
    business_unit_id: int | None = None,
    department_id: int | None = None,
    grade: Literal["L1", "L2", "L3", "L4", "L5", "L6"] | None = None,
    employment_status: Literal["active", "separated"] | None = None,
    location: str | None = None,
    q: str | None = None,
    sort_by: SortBy = "full_name",
    sort_dir: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EmployeeListResponse:
    filtered = _apply_filters(
        select(Employee),
        business_unit_id=business_unit_id,
        department_id=department_id,
        grade=grade,
        employment_status=employment_status,
        location=location,
        q=q,
    )

    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0

    column = SORT_COLUMNS[sort_by]
    order = column.asc() if sort_dir == "asc" else column.desc()
    paged = _with_relations(filtered).order_by(order).limit(limit).offset(offset)
    rows = db.scalars(paged).all()

    return EmployeeListResponse(items=list(rows), total=total, limit=limit, offset=offset)


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
) -> Employee:
    stmt = _with_relations(select(Employee).where(Employee.id == employee_id))
    employee = db.scalar(stmt)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee
```

- [ ] **Step 4: Register the router**

In `backend/app/main.py`, change:
```python
from app.routers import auth
```
to:
```python
from app.routers import auth, employees
```

And change:
```python
app.include_router(auth.router)
```
to:
```python
app.include_router(auth.router)
app.include_router(employees.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_employees.py -v`
Expected: all 11 tests PASS.

If `test_missing_rls_context_returns_empty_not_error` fails with rows returned instead of empty: check that `.env`'s `DATABASE_URL` points at the `fri_app` role, not `fri_migrator` — that test only proves anything if the connection is the RLS-restricted one.

If any BU-head test unexpectedly sees cross-BU data: check `app/security/deps.py`'s `_set_rls_context` is still wired into `get_current_user` — this router adds no filtering, so a regression there would silently break every isolation guarantee this endpoint has.

- [ ] **Step 6: Run the full suite together**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests across `test_jwt.py` and `test_employees.py` PASS (Task 2's `test_smoke.py` was deleted this task).

- [ ] **Step 7: Remove the superseded smoke test and commit**

```bash
git rm backend/tests/test_smoke.py
git add backend/app/routers/employees.py backend/app/main.py backend/tests/test_employees.py
git commit -m "Add employee directory endpoint, enforced entirely by RLS

GET /employees and GET /employees/{id} add no role-derived filtering —
scoping comes from the SET LOCAL session variables get_current_user
already establishes per-request, and the RLS policies from migration
5c6bf1a73a67 do the rest. sort_by is a closed Literal indexing a
hardcoded column dict, never getattr(). Full suite proves BU isolation,
column-level scoping, the manager-across-BU null case, and the
missing-RLS-context fail-closed path through the real HTTP request path."
```

---

### Task 5: Documentation sync

**Files:**
- Modify: `ARCHITECTURE.md` (two locations: Stack section, Security guardrails section)
- Modify: `backend/README.md` (Tests section)

**Interfaces:**
- Consumes: nothing (docs only).
- Produces: nothing consumed by code — verified by grep, not tests.

- [ ] **Step 1: Update ARCHITECTURE.md's Stack section**

Find:
```
- **Auth**: JWT (HS256, 30-minute access tokens, no refresh tokens), stored in an httpOnly/Secure cookie.
```
Replace with:
```
- **Auth**: JWT (HS256, 15-minute access tokens, no refresh tokens), stored in an httpOnly/Secure cookie.
```

- [ ] **Step 2: Update ARCHITECTURE.md's Security guardrails section**

Find:
```
- **Auth**: JWT HS256, 30-minute expiry, no refresh tokens, httpOnly + Secure cookie — never localStorage.
```
Replace with:
```
- **Auth**: JWT HS256, 15-minute expiry, no refresh tokens, httpOnly + Secure cookie — never localStorage. Logout clears the cookie client-side but does not revoke the token server-side (no denylist) — a copied/stolen token remains valid for up to 15 minutes after logout. This is an accepted tradeoff for internal office use on shared/unlocked machines, where the realistic risk is device access rather than token interception in transit; deliberately not building revocation for that threat model.
```

- [ ] **Step 3: Update backend/README.md's Tests section**

Find:
```
## Tests

None yet — Module 1 is schema + auth only per the kickoff brief. Add a test
suite alongside the first router that does real query logic (directory
listing), so the sort/filter column allow-list has something to test
against.
```
Replace with:
```
## Tests

`backend/tests/` — pytest, run against the real local `fri_dev` database
(no mocking; the point is proving Row-Level Security holds through the
real request path, not a stand-in for it). Requires the venv, migrations,
and seed data already set up per the steps above.

```bash
cd backend
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest -v
```

Covers: JWT expiry, and the employee directory endpoint's BU isolation
(HR sees all, BU Head sees only their own BU, cross-BU access by ID and
by filter both return empty/404 rather than an error, compensation
fields are never returned for a row the caller can't see, gender/DOB/phone
never appear in any response, a manager in a different BU resolves to
`null` rather than leaking a name, and a missing RLS session context
returns zero rows rather than erroring).
```

- [ ] **Step 4: Verify no other references to the old 30-minute value remain**

Run (from repo root): `grep -rn "30-minute\|30 min\|JWT_EXPIRE_MINUTES=30\|jwt_expire_minutes: int = 30" --include="*.md" --include="*.py" --include="*.example" .`
Expected: no output (empty).

- [ ] **Step 5: Commit**

```bash
git add ARCHITECTURE.md backend/README.md
git commit -m "Sync docs: 15-minute token everywhere, document logout non-revocation, point README at the new test suite"
```

---

### Task 6: Final full-suite run, manual HTTP spot-check, push

**Files:** none (verification only).

**Interfaces:** none — this task consumes everything built in Tasks 1–5 and produces the final pushed state.

- [ ] **Step 1: Run the complete test suite one more time from a clean process**

Run (from `backend/`): `.venv/Scripts/python.exe -m pytest -v`
Expected: every test PASSes (JWT expiry: 2 tests; employee directory: 11 tests).

- [ ] **Step 2: Start the server and manually confirm the new cookie lifetime**

Run: `.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (background)

```bash
curl -s -i -X POST http://127.0.0.1:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"priya.sharma@lsdigital-demo.com","password":"ChangeMe123!"}' | grep -i set-cookie
```
Expected: `Max-Age=900` (15 × 60), not `Max-Age=1800`.

- [ ] **Step 3: Manually confirm the endpoint through curl as an extra sanity check beyond pytest**

```bash
curl -s -c /tmp/hr.jar -X POST http://127.0.0.1:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"priya.sharma@lsdigital-demo.com","password":"ChangeMe123!"}' >/dev/null
curl -s -b /tmp/hr.jar "http://127.0.0.1:8000/employees?limit=5" | head -c 500
```
Expected: a 200 with a JSON body containing `"items"`, `"total"`, `"limit"`, `"offset"` — confirms the route is live outside the test process too, not only under `TestClient`.

Stop the server afterward.

- [ ] **Step 4: Confirm git state is clean and push**

```bash
cd "C:/Users/Utkarsh/Documents/AI Projects/Flight Risk Intelligence"
git status --short
git log --oneline -8
git push origin new-fri
```
Expected: clean working tree before push, and the push succeeds against `origin/new-fri`.

---

## Self-Review Notes

- **Spec coverage:** enforcement boundary (Task 4), both endpoints (Task 4), all 6 field exclusions/inclusions (Task 3), sort/filter allow-list (Task 4), pagination shape (Task 3/4), all 10 required test cases from the spec (Task 4 covers 1–10: HR-all, BU-scoped, cross-BU-by-id-404, cross-BU-by-filter-empty, column-scoping, gender-exclusion, manager-null, missing-RLS-empty, sort-reject, sort-allow), JWT 15-minute change (Task 1), both ARCHITECTURE.md locations + logout-non-revocation note + README (Task 5).
- **Placeholder scan:** none found — every step has literal code or literal commands with expected output.
- **Type consistency:** `EmployeeOut`/`EmployeeListResponse` (Task 3) match the router's imports and return types (Task 4) exactly; fixture dict keys from `conftest.py` (Task 2) match every access in `test_employees.py` (Task 4).
