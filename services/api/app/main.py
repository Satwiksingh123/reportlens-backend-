from fastapi import FastAPI

from app.api import routes_auth, routes_reports
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="ReportLens API",
    version="0.1.0",
    description="Self-hosted, evidence-grounded lab-report explainer.",
)

app.include_router(routes_auth.router)
app.include_router(routes_reports.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
