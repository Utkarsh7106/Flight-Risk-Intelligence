"""Module 4, Part B — the shareable Workforce Health report.

Renders one self-contained HTML document that is used two ways: served
directly as the "HTML export" (see app/routers/exports.py), and printed
to PDF by a headless Chromium (see app/exports/pdf.py) for the "PDF
export". The two formats therefore can't visually drift apart — there is
exactly one template, not a second one hand-maintained for print.

Self-contained means self-contained: no <link> to the live API, no
Google Fonts / CDN reference (the live app loads Inter from Google Fonts
in index.html; this document deliberately does not, and falls back to
the same system-font stack tokens.css already specifies for that case),
no image URLs pointing at anything other than an inline data: URI. This
file is opened, potentially much later, on a machine with no access to
this backend at all — see MODULE4_REFERENCE.md's "Self-contained means
self-contained".

Scope (what data this renders) is decided entirely by the caller
(app/routers/exports.py) via RLS + an optional business_unit_id filter —
this module has no opinion on access control and receives only data the
caller has already determined the requester may see.

Deliberately excluded from this report, in every scope, for every role:
the fairness audit (HR-only everywhere in this app, including here — see
MODULE4_REFERENCE.md) and anything from Module 3's synthetic/demonstration
dataset. The latter is a scope decision, not an oversight: keeping this
report's data story to a single source (the real Module 1/2 baseline
panel and its transparent scorecard) means there is no risk of the
"demonstration dataset" labeling requirement ever silently failing to
carry through a future change to this template — see MODULE4_REFERENCE.md's
"if a shared export includes anything derived from Module 3's
demonstration dataset" and this module's docstring in
app/routers/exports.py for the full reasoning. A future session adding
a Module 3 export should give it its own equally prominent, independently
verified demo-dataset treatment rather than reusing this one.

The employee-level baseline panel itself is not real/live company data
(see ARCHITECTURE.md, "The baseline dataset is not live data") — the
live app currently only documents this rather than displaying it, but an
export is a document that leaves the app and can be handed to someone
with no other context, so this template says so explicitly in its
footer. This is a small, deliberate strengthening beyond what the live
screens currently do, made here because the consequence of the omission
is higher on a standalone document than on an authenticated in-app
screen.
"""

from __future__ import annotations

import datetime as dt
import html
from dataclasses import dataclass

from app.scoring.employee_scoring import ScoredEmployee

BAND_COLORS: dict[str, tuple[str, str, str]] = {
    # (line color, bg, text) — same values as frontend/src/styles/tokens.css's
    # --color-risk-*/--color-risk-*-bg/--color-risk-*-text, copied rather
    # than shared, since this is a standalone Python template with no
    # access to the frontend's CSS at all.
    "low": ("#059669", "#ecfdf5", "#047857"),
    "medium": ("#f59e0b", "#fffbeb", "#b45309"),
    "high": ("#dc2626", "#fef2f2", "#b91c1c"),
    "critical": ("#7f1d1d", "#fee2e2", "#7f1d1d"),
}
BAND_LABELS = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}
BAND_ORDER = ("low", "medium", "high", "critical")


@dataclass(frozen=True)
class BusinessUnitRow:
    name: str
    employee_count: int
    average_score: float
    band_counts: dict[str, int]


def _esc(value: object) -> str:
    return html.escape(str(value)) if value is not None else "—"


def _band_bar_html(band_counts: dict[str, int]) -> str:
    total = sum(band_counts.values()) or 1
    segments = "".join(
        f'<div style="flex:{band_counts.get(band, 0)};background:{BAND_COLORS[band][0]};min-width:'
        f'{"2px" if band_counts.get(band, 0) else "0"};" title="{BAND_LABELS[band]}: {band_counts.get(band, 0)}"></div>'
        for band in BAND_ORDER
    )
    legend = "".join(
        f'<span class="legend-item"><span class="legend-dot" style="background:{BAND_COLORS[band][0]}"></span>'
        f"{BAND_LABELS[band]} {band_counts.get(band, 0)}</span>"
        for band in BAND_ORDER
    )
    return f'<div class="band-bar">{segments}</div><div class="legend">{legend}</div>'


def _business_units_table_html(business_units: list[BusinessUnitRow]) -> str:
    if len(business_units) <= 1:
        return ""
    rows = "".join(
        f"<tr><td>{_esc(bu.name)}</td><td class='num'>{bu.employee_count}</td>"
        f"<td class='num'>{bu.average_score:.1f}</td><td>{_band_bar_html(bu.band_counts)}</td></tr>"
        for bu in sorted(business_units, key=lambda b: b.average_score, reverse=True)
    )
    return f"""
    <section>
      <h2>Business Units</h2>
      <table>
        <thead><tr><th>Business Unit</th><th>Employees</th><th>Avg. Score</th><th>Risk Distribution</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def _employee_rows_html(scored: list[ScoredEmployee]) -> str:
    rows = []
    for item in sorted(scored, key=lambda s: s.result.score, reverse=True):
        e, r = item.employee, item.result
        band_color = BAND_COLORS[r.band.value]
        rows.append(
            "<tr>"
            f"<td>{_esc(e.full_name)}</td>"
            f"<td class='mono'>{_esc(e.employee_code)}</td>"
            f"<td>{_esc(e.business_unit.name)}<br><span class='muted'>{_esc(e.department.name)}</span></td>"
            f"<td>{_esc(e.grade)}</td>"
            f"<td>{_esc(e.designation)}</td>"
            f"<td class='num'>{r.score:.0f}</td>"
            f"<td><span class='badge' style=\"background:{band_color[1]};color:{band_color[2]}\">"
            f"{BAND_LABELS[r.band.value]}</span></td>"
            "</tr>"
        )
    return "".join(rows)


def render_workforce_health_report_html(
    *,
    scope_label: str,
    generated_by_name: str,
    generated_by_role_label: str,
    generated_at: dt.datetime,
    employee_count: int,
    average_score: float,
    band_counts: dict[str, int],
    business_units: list[BusinessUnitRow],
    scored_employees: list[ScoredEmployee],
    interactive: bool = True,
) -> str:
    """`interactive=False` drops the client-side search box — used for the
    PDF render, where a search input has no purpose on a static printed
    page (see app/exports/pdf.py).
    """
    generated_at_label = generated_at.strftime("%d %b %Y, %H:%M IST")
    filter_box = (
        """
        <input id="employee-filter" type="search" placeholder="Filter by name, code, or department…"
               oninput="filterEmployees(this.value)" />
        """
        if interactive
        else ""
    )
    filter_script = (
        """
        <script>
          function filterEmployees(query) {
            var q = query.trim().toLowerCase();
            document.querySelectorAll('#employee-table tbody tr').forEach(function (row) {
              row.style.display = row.textContent.toLowerCase().indexOf(q) === -1 ? 'none' : '';
            });
          }
        </script>
        """
        if interactive
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Flight Risk Intelligence — Workforce Health Report</title>
<style>
  :root {{
    --navy: #0f172a; --slate: #334155; --on-surface: #191c1e; --on-surface-variant: #45464d;
    --surface: #f7f9fb; --border: #e2e8f0;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
    color: var(--on-surface); background: #ffffff; margin: 0; padding: 32px;
    max-width: 960px; margin-inline: auto;
  }}
  header {{ border-bottom: 2px solid var(--navy); padding-bottom: 16px; margin-bottom: 24px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; color: var(--navy); }}
  .meta {{ color: var(--on-surface-variant); font-size: 13px; }}
  .kpi-row {{ display: flex; gap: 16px; margin-bottom: 24px; }}
  .kpi {{ flex: 1; border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; }}
  .kpi-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--on-surface-variant); }}
  .kpi-value {{ font-size: 26px; font-weight: 700; margin-top: 4px; }}
  section {{ margin-bottom: 28px; }}
  h2 {{ font-size: 16px; color: var(--navy); border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em;
        color: var(--on-surface-variant); padding: 8px; border-bottom: 1px solid var(--border); }}
  td {{ padding: 8px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  tr {{ break-inside: avoid; page-break-inside: avoid; }}
  thead {{ display: table-header-group; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .muted {{ color: var(--on-surface-variant); font-size: 11px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
  .band-bar {{ display: flex; height: 10px; border-radius: 4px; overflow: hidden; background: var(--border); min-width: 160px; }}
  .legend {{ display: flex; gap: 10px; margin-top: 4px; font-size: 11px; color: var(--on-surface-variant); flex-wrap: wrap; }}
  .legend-item {{ display: inline-flex; align-items: center; gap: 4px; }}
  .legend-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
  #employee-filter {{
    width: 100%; padding: 8px 12px; margin-bottom: 12px; border: 1px solid var(--border);
    border-radius: 6px; font-size: 13px; font-family: inherit;
  }}
  footer {{ margin-top: 32px; padding-top: 12px; border-top: 1px solid var(--border);
            font-size: 11px; color: var(--on-surface-variant); }}
  @media print {{
    body {{ padding: 0; }}
    #employee-filter {{ display: none; }}
  }}
</style>
</head>
<body>
  <header>
    <h1>Flight Risk Intelligence — Workforce Health Report</h1>
    <div class="meta">
      {_esc(scope_label)} &middot; Generated {generated_at_label} by {_esc(generated_by_name)}
      ({_esc(generated_by_role_label)})
    </div>
  </header>

  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">Employees Scored</div><div class="kpi-value">{employee_count}</div></div>
    <div class="kpi"><div class="kpi-label">Average Score</div><div class="kpi-value">{average_score:.1f}</div></div>
  </div>

  <section>
    <h2>Risk Band Distribution</h2>
    {_band_bar_html(band_counts)}
  </section>

  {_business_units_table_html(business_units)}

  <section>
    <h2>Employees</h2>
    {filter_box}
    <table id="employee-table">
      <thead>
        <tr><th>Employee</th><th>Code</th><th>Business Unit / Dept</th><th>Grade</th><th>Designation</th>
            <th>Score</th><th>Band</th></tr>
      </thead>
      <tbody>{_employee_rows_html(scored_employees)}</tbody>
    </table>
  </section>

  <footer>
    Flight Risk Intelligence — a proof-of-concept HR attrition dashboard built for LS Digital.
    The Workforce Health score is a transparent, hand-weighted scorecard, not a trained model
    (see the live app's driver breakdown for the full reasoning behind each score). Employee
    records in this report are an illustrative baseline panel used for product demonstration —
    not real or live LS Digital company data.
  </footer>

  {filter_script}
</body>
</html>"""
