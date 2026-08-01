"""Chooses how an uploaded report's pipeline actually runs.

Keeping this in one place means the upload endpoint doesn't care which mode is configured,
and each mode's caveats are documented where the decision is made rather than at the call
site. See Settings.pipeline_mode for what each mode is for.
"""

import atexit
import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# One small pool rather than a thread per upload: the pipeline is CPU-heavy (OCR) and
# calls a local LLM, so running many at once on a dev box thrashes rather than helps.
# Created lazily so the "celery" and "inline" modes never spin up threads they won't use.
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipeline")
        # Don't let a shutdown mid-report leave a half-written report row behind silently -
        # wait briefly for in-flight work so status/error columns get their final commit.
        atexit.register(lambda: _executor and _executor.shutdown(wait=True))
    return _executor


def _run_and_log(report_id: int) -> None:
    from app.tasks.pipeline import process_report

    try:
        # .run() executes the task body directly - no broker, no Celery result plumbing.
        process_report.run(report_id)
    except Exception:  # noqa: BLE001 - a background thread must never die silently
        logger.exception("Background pipeline failed for report %s", report_id)


def dispatch_pipeline(report_id: int) -> None:
    """Start (or run) the processing pipeline for a report, per the configured mode."""
    from app.tasks.pipeline import process_report

    mode = settings.pipeline_mode

    if mode == "celery":
        process_report.delay(report_id)
        return

    if mode == "thread":
        _get_executor().submit(_run_and_log, report_id)
        return

    if mode == "inline":
        # .run() rather than .delay()/.apply(): Celery resolves the broker transport before
        # it checks any eager flag, so those would still try to reach Redis and fail when
        # none is configured. .run() bypasses Celery entirely.
        process_report.run(report_id)
        return

    raise ValueError(f"unknown pipeline_mode: {mode!r}")
