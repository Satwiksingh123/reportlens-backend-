import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReportStatus(enum.StrEnum):
    uploaded = "uploaded"
    ocr_running = "ocr_running"
    parsing = "parsing"
    explaining = "explaining"
    completed = "completed"
    failed = "failed"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(512))
    stored_path: Mapped[str] = mapped_column(String(1024))
    content_type: Mapped[str] = mapped_column(String(128))
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), default=ReportStatus.uploaded, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="reports")  # noqa: F821
    results: Mapped[list["StructuredResult"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class StructuredResult(Base):
    """One parsed biomarker row from a report."""

    __tablename__ = "structured_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    panel: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. "CBC"
    test_name: Mapped[str] = mapped_column(String(256))
    value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # Low/Normal/High
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # RAG source refs

    report: Mapped["Report"] = relationship(back_populates="results")
