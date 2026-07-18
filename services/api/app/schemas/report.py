from datetime import datetime

from pydantic import BaseModel

from app.models.report import ReportStatus


class StructuredResultOut(BaseModel):
    panel: str | None = None
    test_name: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    status: str | None = None
    explanation: str | None = None
    evidence: dict | None = None

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: int
    original_filename: str
    status: ReportStatus
    summary: str | None = None
    error_message: str | None = None
    created_at: datetime
    results: list[StructuredResultOut] = []

    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    id: int
    original_filename: str
    status: ReportStatus
    created_at: datetime

    class Config:
        from_attributes = True
