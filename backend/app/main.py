from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, departure_events, employees, exports, risk_analysis, workforce_health

app = FastAPI(title="Flight Risk Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Content-Disposition isn't on the browser's small CORS-safelisted
    # header set by default, so a cross-origin fetch() (this app's
    # frontend and backend are always different origins — different dev
    # ports locally, different hosts in production per ARCHITECTURE.md)
    # can't read the filename Module 4's export endpoint sets unless it's
    # explicitly exposed here. Found live: without this, every export
    # downloaded as a generic "workforce-health-export.html" instead of
    # the real fri-workforce-health-<scope>-<date> filename.
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(workforce_health.router)
app.include_router(risk_analysis.router)
app.include_router(departure_events.router)
app.include_router(exports.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
