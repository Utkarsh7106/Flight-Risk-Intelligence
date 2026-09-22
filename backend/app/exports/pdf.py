"""Renders a self-contained HTML string (see workforce_health_report.py)
to PDF bytes via headless Chromium, so the PDF and HTML exports are
guaranteed to look the same — one template, one CSS, two output formats.

Deliberately not weasyprint/reportlab: this app already has zero
dependency on any HTML/CSS rendering engine other than a real browser,
and a real browser's print pipeline (proper @page handling, real
CSS support) is what makes the PDF read as an actually finished
document rather than a naive HTML-to-PDF conversion. The cost is a real
one, documented rather than hidden: Playwright's Chromium becomes a
genuine runtime dependency of the live API (see requirements.txt), and
the backend host (Render/Railway, per ARCHITECTURE.md's deployment
section) needs `playwright install chromium` as a deploy step, not
something Render/Railway provide by default the way they provide
Postgres connectivity — this is a real, new deployment consideration
Utkarsh should know about before deploying, not before building this
feature (see PROJECT_VISION.md's "keep moving" directive: this isn't a
security decision or a broken foundation, it's an infrastructure cost
worth a note, not a reason to stop and wait).

A new Chromium process per request is the deliberately simple choice for
this proof-of-concept's traffic level (an HR pitch tool, not a
high-throughput service) — launching once per request rather than
maintaining a long-lived browser pool. Revisit only if export traffic
ever makes that latency actually matter.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from app.config import settings


def render_html_to_pdf(html_document: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=settings.playwright_chromium_executable_path or None)
        try:
            page = browser.new_page()
            page.set_content(html_document, wait_until="load")
            return page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
            )
        finally:
            browser.close()
