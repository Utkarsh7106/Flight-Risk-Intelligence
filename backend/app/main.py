from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, departure_events, employees, risk_analysis, workforce_health

app = FastAPI(title="Flight Risk Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(workforce_health.router)
app.include_router(risk_analysis.router)
app.include_router(departure_events.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
