"""Async orchestration of the full ReportLens pipeline.

Each stage is a placeholder that will delegate to the dedicated service package
(ocr_engine, medical_parser, rag, llm_service) once those are wired in. For now the
stages are stubbed so the end-to-end flow and status transitions work.
"""

import logging

from app.core.database import SessionLocal
from app.models.report import Report, ReportStatus, StructuredResult
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="pipeline.process_report")
def process_report(report_id: int) -> None:
    db = SessionLocal()
    try:
        report = db.get(Report, report_id)
        if report is None:
            logger.warning("Report %s not found", report_id)
            return

        # 1. OCR
        report.status = ReportStatus.ocr_running
        db.commit()
        raw_text = _run_ocr(report.stored_path, report.content_type)
        report.raw_ocr_text = raw_text

        # 2. Parse
        report.status = ReportStatus.parsing
        db.commit()
        parsed_rows = _run_parser(raw_text)

        # 3. Explain (RAG + LLM)
        report.status = ReportStatus.explaining
        db.commit()
        enriched_rows, summary = _run_explainer(parsed_rows)

        for row in enriched_rows:
            db.add(StructuredResult(report_id=report.id, **_result_kwargs(row)))
        report.summary = summary
        report.status = ReportStatus.completed
        db.commit()
        logger.info("Report %s completed", report_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for report %s", report_id)
        report = db.get(Report, report_id)
        if report:
            report.status = ReportStatus.failed
            report.error_message = str(exc)
            db.commit()
    finally:
        db.close()


_RESULT_COLUMNS = {
    "panel",
    "test_name",
    "value",
    "unit",
    "reference_range",
    "status",
    "explanation",
    "evidence",
}


def _result_kwargs(row: dict) -> dict:
    """Project an enriched explainer row onto StructuredResult columns.

    Keys the model has no column for (e.g. guardrail_flags) are folded into the evidence
    JSON so nothing is silently lost and the insert stays schema-safe.
    """
    kwargs = {k: v for k, v in row.items() if k in _RESULT_COLUMNS}
    flags = row.get("guardrail_flags")
    if flags:
        evidence = dict(kwargs.get("evidence") or {})
        evidence["guardrail_flags"] = flags
        kwargs["evidence"] = evidence
    return kwargs


# --- stage stubs (replaced by real service calls incrementally) ---


def _run_ocr(path: str, content_type: str) -> str:
    from app.services.ocr_client import extract_text

    return extract_text(path, content_type)


def _run_parser(raw_text: str) -> list[dict]:
    from app.services.parser_client import parse

    return parse(raw_text)


def _run_explainer(rows: list[dict]) -> tuple[list[dict], str]:
    from app.services.llm_client import explain

    return explain(rows)
