from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.employee import Employee


def _payload(employee_id: int, **overrides) -> dict:
    body = {
        "employee_id": employee_id,
        "departure_date": "2026-08-01",
        "departure_type": "voluntary",
        "reason_category": "better_opportunity",
    }
    body.update(overrides)
    return body


# --- Write path -------------------------------------------------------


def test_hr_can_record_departure_for_any_bu(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["other_employee_id"]))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["employee"]["id"] == seeded_employees["other_employee_id"]
    assert body["departure_type"] == "voluntary"
    assert body["reason_category"] == "better_opportunity"
    assert body["recorded_by"]["full_name"] == "Priya Sharma"
    # business_unit/department are snapshotted from the employee's own
    # current values server-side, never accepted from the request body.
    assert body["business_unit"]["id"] == seeded_employees["other_bu_id"]


def test_bu_head_can_record_departure_for_own_bu_employee(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert resp.status_code == 201, resp.text
    assert resp.json()["employee"]["id"] == seeded_employees["own_employee_id"]


def test_bu_head_recording_departure_for_other_bu_employee_is_404(
    bu_head_client: TestClient, seeded_employees: dict
):
    """Mirrors every other cross-BU lookup's honest-404 pattern in this
    app: a BU Head asking about an employee_id they can't see gets the
    same response as an employee_id that doesn't exist at all, never a
    403 that would confirm the id is real.
    """
    resp = bu_head_client.post("/departure-events", json=_payload(seeded_employees["other_employee_id"]))
    assert resp.status_code == 404


def test_recording_departure_for_already_separated_employee_is_409(hr_client: TestClient, seeded_employees: dict):
    first = hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert first.status_code == 201

    second = hr_client.post(
        "/departure-events", json=_payload(seeded_employees["own_employee_id"], departure_date="2026-09-01")
    )
    assert second.status_code == 409


def test_departure_date_before_joining_date_is_rejected(hr_client: TestClient, seeded_employees: dict):
    # own_employee's date_of_joining is 2022-06-01 (see conftest.seeded_employees)
    resp = hr_client.post(
        "/departure-events",
        json=_payload(seeded_employees["own_employee_id"], departure_date="2020-01-01"),
    )
    assert resp.status_code == 422


def test_reason_category_must_match_departure_type(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.post(
        "/departure-events",
        json=_payload(
            seeded_employees["own_employee_id"],
            departure_type="voluntary",
            reason_category="performance_managed_out",  # an involuntary-only category
        ),
    )
    assert resp.status_code == 422


def test_reason_category_is_optional(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.post(
        "/departure-events",
        json={
            "employee_id": seeded_employees["own_employee_id"],
            "departure_date": "2026-08-01",
            "departure_type": "other",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["reason_category"] is None


# --- Trigger effect -----------------------------------------------------


def test_recording_departure_flips_employment_status(
    hr_client: TestClient, seeded_employees: dict, migrator_session
):
    before = migrator_session.scalar(select(Employee).where(Employee.id == seeded_employees["own_employee_id"]))
    assert before.employment_status == "active"

    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert resp.status_code == 201

    migrator_session.expire_all()
    after = migrator_session.scalar(select(Employee).where(Employee.id == seeded_employees["own_employee_id"]))
    assert after.employment_status == "separated"


# --- Default-hidden, explicit-filter-reachable --------------------------


def test_separated_employee_excluded_from_default_directory(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert resp.status_code == 201

    default_listing = hr_client.get("/employees", params={"limit": 200})
    ids = {item["id"] for item in default_listing.json()["items"]}
    assert seeded_employees["own_employee_id"] not in ids


def test_separated_employee_reachable_via_explicit_filter(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert resp.status_code == 201

    separated_listing = hr_client.get("/employees", params={"employment_status": "separated", "limit": 200})
    ids = {item["id"] for item in separated_listing.json()["items"]}
    assert seeded_employees["own_employee_id"] in ids

    all_listing = hr_client.get("/employees", params={"employment_status": "all", "limit": 200})
    all_ids = {item["id"] for item in all_listing.json()["items"]}
    assert seeded_employees["own_employee_id"] in all_ids


def test_separated_employee_excluded_from_workforce_health_summary(hr_client: TestClient, seeded_employees: dict):
    before_summary = hr_client.get("/workforce-health/summary").json()

    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert resp.status_code == 201

    after_summary = hr_client.get("/workforce-health/summary").json()
    assert after_summary["employee_count"] == before_summary["employee_count"] - 1
    after_hotspot_ids = {h["employee_id"] for h in after_summary["hotspots"]}
    assert seeded_employees["own_employee_id"] not in after_hotspot_ids


def test_separated_employee_score_404s_by_default(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert resp.status_code == 201

    resp = hr_client.get(f"/workforce-health/employees/{seeded_employees['own_employee_id']}")
    assert resp.status_code == 404


def test_separated_employee_score_reachable_via_explicit_filter(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert resp.status_code == 201

    separated = hr_client.get(
        f"/workforce-health/employees/{seeded_employees['own_employee_id']}",
        params={"employment_status": "separated"},
    )
    assert separated.status_code == 200
    assert separated.json()["employee_id"] == seeded_employees["own_employee_id"]

    everyone = hr_client.get(
        f"/workforce-health/employees/{seeded_employees['own_employee_id']}",
        params={"employment_status": "all"},
    )
    assert everyone.status_code == 200
    assert everyone.json()["employee_id"] == seeded_employees["own_employee_id"]


def test_bu_head_separated_own_employee_score_404s_by_default_but_reachable_via_opt_in(
    hr_client: TestClient, bu_head_client: TestClient, seeded_employees: dict
):
    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    assert resp.status_code == 201

    default = bu_head_client.get(f"/workforce-health/employees/{seeded_employees['own_employee_id']}")
    assert default.status_code == 404

    opted_in = bu_head_client.get(
        f"/workforce-health/employees/{seeded_employees['own_employee_id']}",
        params={"employment_status": "all"},
    )
    assert opted_in.status_code == 200
    assert opted_in.json()["employee_id"] == seeded_employees["own_employee_id"]


def test_bu_head_cannot_reach_other_bus_separated_employee_score_even_with_opt_in(
    hr_client: TestClient, bu_head_client: TestClient, seeded_employees: dict
):
    """Mirrors test_bu_head_recording_departure_for_other_bu_employee_is_404's
    honest-404 pattern: employment_status is a separate dimension from BU
    scoping, and the opt-in must never widen RLS — a BU Head asking with
    ?employment_status=all for another BU's separated employee gets the
    same 404 as for an id that doesn't exist at all.
    """
    resp = hr_client.post("/departure-events", json=_payload(seeded_employees["other_employee_id"]))
    assert resp.status_code == 201

    for params in (None, {"employment_status": "separated"}, {"employment_status": "all"}):
        resp = bu_head_client.get(
            f"/workforce-health/employees/{seeded_employees['other_employee_id']}",
            params=params,
        )
        assert resp.status_code == 404


# --- RLS-scoped listing of departure_event itself ------------------------


def test_hr_sees_departure_events_across_bus(hr_client: TestClient, seeded_employees: dict):
    hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    hr_client.post("/departure-events", json=_payload(seeded_employees["other_employee_id"]))

    resp = hr_client.get("/departure-events", params={"limit": 200})
    assert resp.status_code == 200
    ids = {item["employee"]["id"] for item in resp.json()["items"]}
    assert seeded_employees["own_employee_id"] in ids
    assert seeded_employees["other_employee_id"] in ids


def test_bu_head_sees_only_own_bu_departure_events(
    hr_client: TestClient, bu_head_client: TestClient, seeded_employees: dict
):
    hr_client.post("/departure-events", json=_payload(seeded_employees["own_employee_id"]))
    hr_client.post("/departure-events", json=_payload(seeded_employees["other_employee_id"]))

    resp = bu_head_client.get("/departure-events", params={"limit": 200})
    assert resp.status_code == 200
    body = resp.json()
    ids = {item["employee"]["id"] for item in body["items"]}
    assert seeded_employees["own_employee_id"] in ids
    assert seeded_employees["other_employee_id"] not in ids
    for item in body["items"]:
        assert item["business_unit"]["id"] == seeded_employees["bu_head_bu_id"]


def test_sort_by_disallowed_value_is_rejected(hr_client: TestClient):
    resp = hr_client.get("/departure-events", params={"sort_by": "reason_notes"})
    assert resp.status_code == 422
