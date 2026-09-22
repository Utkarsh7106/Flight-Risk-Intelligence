"""Shareable exports — Module 4, Part B.

Two formats over one template (app/exports/workforce_health_report.py):
an interactive-ish self-contained HTML file, and a PDF rendered from that
same HTML by headless Chromium (app/exports/pdf.py) — see both modules'
docstrings for why a single template and why Chromium.

Scope and access control, same discipline as every other router in this
app: RLS still runs (nothing here bypasses app.current_role/
app.current_bu_id), and business_unit_id is an *additional* filter this
router applies on top of whatever RLS already restricted the query to.
For a BU Head, business_unit_id is never taken from the client — it's
forced to their own business_unit_id, so their export can never even
attempt to be about a BU they don't lead: not because RLS wouldn't
already block a mismatched export (it would, and would just return zero
rows), but because forcing it server-side means their export's *peer
group* is always computed the right way (their own BU only) rather than
depending on the client happening to pass the right value or nothing at
all. HR may omit business_unit_id for an org-wide report or pass one to
get exactly what that BU's own BU Head would see live — see
app/scoring/employee_scoring.py's docstring for why that's the right
scope for peer-group computation, not just row filtering.

No fairness-audit content is reachable from this router at all — there's
no code path here that ever touches app/scoring/fairness_audit.py, so
there's nothing to gate; this is a stronger guarantee than a role check
that could be gotten wrong. See MODULE4_REFERENCE.md.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exports.pdf import render_html_to_pdf
from app.exports.workforce_health_report import BusinessUnitRow, render_workforce_health_report_html
from app.models.app_user import AppUser
from app.models.business_unit import BusinessUnit
from app.scoring.employee_scoring import score_active_employees
from app.security.deps import get_current_user

router = APIRouter(prefix="/exports", tags=["exports"])

ROLE_LABELS = {"hr": "HR", "bu_head": "BU Head"}


def _resolve_scope(
    db: Session, current_user: AppUser, requested_business_unit_id: int | None
) -> tuple[int | None, str]:
    """Returns (effective_business_unit_id, scope_label)."""
    if current_user.role == "bu_head":
        # Never trust a client-supplied value for a BU Head — always their
        # own BU, matching what they'd see live everywhere else in this app.
        business_unit_id = current_user.business_unit_id
    else:
        business_unit_id = requested_business_unit_id

    if business_unit_id is None:
        return None, "Org-wide — every business unit"

    bu = db.get(BusinessUnit, business_unit_id)
    if bu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business unit not found")
    return business_unit_id, f"{bu.name} business unit"


def _build_report_html(db: Session, current_user: AppUser, business_unit_id: int | None, *, interactive: bool) -> str:
    effective_bu_id, scope_label = _resolve_scope(db, current_user, business_unit_id)
    scored = score_active_employees(db, business_unit_id=effective_bu_id)

    band_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    bu_groups: dict[int, dict] = {}
    for item in scored:
        band_counts[item.result.band.value] += 1
        bucket = bu_groups.setdefault(
            item.employee.business_unit_id,
            {"name": item.employee.business_unit.name, "scores": [], "bands": {"low": 0, "medium": 0, "high": 0, "critical": 0}},
        )
        bucket["scores"].append(item.result.score)
        bucket["bands"][item.result.band.value] += 1

    business_units = [
        BusinessUnitRow(
            name=data["name"],
            employee_count=len(data["scores"]),
            average_score=round(sum(data["scores"]) / len(data["scores"]), 1),
            band_counts=data["bands"],
        )
        for data in bu_groups.values()
    ]
    average_score = round(sum(item.result.score for item in scored) / len(scored), 1) if scored else 0.0

    return render_workforce_health_report_html(
        scope_label=scope_label,
        generated_by_name=current_user.full_name,
        generated_by_role_label=ROLE_LABELS.get(current_user.role, current_user.role),
        generated_at=dt.datetime.now(),
        employee_count=len(scored),
        average_score=average_score,
        band_counts=band_counts,
        business_units=business_units,
        scored_employees=scored,
        interactive=interactive,
    )


def _filename_slug(current_user: AppUser, business_unit_id: int | None, db: Session) -> str:
    if business_unit_id is None:
        scope = "org-wide"
    else:
        bu = db.get(BusinessUnit, business_unit_id)
        scope = (bu.name if bu else "business-unit").lower().replace(" ", "-").replace("/", "-")
    date_label = dt.date.today().isoformat()
    return f"fri-workforce-health-{scope}-{date_label}"


@router.get("/workforce-health")
def export_workforce_health(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
    format: Literal["html", "pdf"] = "html",
    business_unit_id: int | None = None,
) -> Response:
    html_document = _build_report_html(db, current_user, business_unit_id, interactive=(format == "html"))
    slug = _filename_slug(current_user, business_unit_id if current_user.role == "hr" else current_user.business_unit_id, db)

    if format == "html":
        return Response(
            content=html_document,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{slug}.html"'},
        )

    pdf_bytes = render_html_to_pdf(html_document)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'},
    )
