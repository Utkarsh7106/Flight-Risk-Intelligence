from __future__ import annotations

from fastapi.testclient import TestClient


def test_html_export_is_self_contained_and_well_formed(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.get("/exports/workforce-health", params={"format": "html"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "attachment" in resp.headers["content-disposition"]
    assert "filename=" in resp.headers["content-disposition"]

    body = resp.text
    assert "<!DOCTYPE html>" in body
    # No external network dependency — the live app loads Inter from
    # Google Fonts (frontend/index.html); this export deliberately does
    # not, per MODULE4_REFERENCE.md's "self-contained means self-contained".
    assert "fonts.googleapis.com" not in body
    assert "http://localhost:8000" not in body
    assert "src=\"http" not in body and "href=\"http" not in body


def test_html_export_org_wide_includes_multiple_bus(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.get("/exports/workforce-health", params={"format": "html"})
    body = resp.text
    assert "Org-wide" in body
    assert "Own BU Employee" in body
    assert "Other BU Employee" in body


def test_html_export_scoped_to_one_bu_excludes_other_bus(hr_client: TestClient, seeded_employees: dict):
    resp = hr_client.get(
        "/exports/workforce-health",
        params={"format": "html", "business_unit_id": seeded_employees["bu_head_bu_id"]},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "business unit" in body  # "<BU name> business unit" scope label, not "Org-wide"
    assert "Own BU Employee" in body
    assert "Other BU Employee" not in body


def test_bu_head_export_is_forced_to_own_bu_regardless_of_param(bu_head_client: TestClient, seeded_employees: dict):
    """A BU Head requesting another BU's id must not get that BU's report —
    the backend overrides business_unit_id server-side for a bu_head, see
    app/routers/exports.py's _resolve_scope().
    """
    resp = bu_head_client.get(
        "/exports/workforce-health",
        params={"format": "html", "business_unit_id": seeded_employees["other_bu_id"]},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "Own BU Employee" in body
    assert "Other BU Employee" not in body


def test_bu_head_cannot_see_other_bu_employees_via_export(bu_head_client: TestClient, seeded_employees: dict):
    resp = bu_head_client.get("/exports/workforce-health", params={"format": "html"})
    assert resp.status_code == 200
    assert "Other BU Employee" not in resp.text


def test_export_never_contains_fairness_audit_content(hr_client: TestClient, seeded_employees: dict):
    """The fairness audit is HR-only everywhere in this app, including
    exports (MODULE4_REFERENCE.md) — but more than that, this export has
    no code path that ever touches app/scoring/fairness_audit.py at all,
    so gender/manager-identity content should never appear in its output
    regardless of role.
    """
    resp = hr_client.get("/exports/workforce-health", params={"format": "html"})
    body_lower = resp.text.lower()
    assert "fairness" not in body_lower
    assert "gender" not in body_lower
    assert "proxy" not in body_lower


def test_export_excludes_separated_employees(hr_client: TestClient, seeded_employees: dict):
    before = hr_client.get("/exports/workforce-health", params={"format": "html"})
    assert "Own BU Employee" in before.text

    departure_resp = hr_client.post(
        "/departure-events",
        json={
            "employee_id": seeded_employees["own_employee_id"],
            "departure_date": "2026-08-01",
            "departure_type": "voluntary",
        },
    )
    assert departure_resp.status_code == 201

    after = hr_client.get("/exports/workforce-health", params={"format": "html"})
    assert "Own BU Employee" not in after.text


def test_export_nonexistent_business_unit_is_404(hr_client: TestClient):
    resp = hr_client.get("/exports/workforce-health", params={"format": "html", "business_unit_id": 999999})
    assert resp.status_code == 404


def test_export_kpi_numbers_match_live_summary(hr_client: TestClient, seeded_employees: dict):
    summary = hr_client.get("/workforce-health/summary").json()
    export = hr_client.get("/exports/workforce-health", params={"format": "html"})
    body = export.text
    assert f'<div class="kpi-value">{summary["employee_count"]}</div>' in body
    assert f'<div class="kpi-value">{summary["average_score"]:.1f}</div>' in body


def test_pdf_export_returns_a_real_pdf(hr_client: TestClient, seeded_employees: dict):
    """Genuinely renders through headless Chromium (app/exports/pdf.py) —
    not mocked — so this proves the whole pipeline works, not just that
    the HTML template string-builds correctly.
    """
    resp = hr_client.get("/exports/workforce-health", params={"format": "pdf"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 1000
