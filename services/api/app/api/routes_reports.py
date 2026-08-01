import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.schemas.report import ReportListItem, ReportOut

router = APIRouter(prefix="/api/reports", tags=["reports"])
settings = get_settings()

ALLOWED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
}


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def upload_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Report:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(settings.upload_dir, stored_name)

    contents = file.file.read()
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    with open(stored_path, "wb") as f:
        f.write(contents)

    report = Report(
        owner_id=user.id,
        original_filename=file.filename or stored_name,
        stored_path=stored_path,
        content_type=file.content_type,
        status=ReportStatus.uploaded,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Kick off processing. How it runs (Celery worker / background thread / inline) is
    # decided by pipeline_mode - see app.tasks.dispatch.
    from app.tasks.dispatch import dispatch_pipeline

    dispatch_pipeline(report.id)

    if settings.pipeline_mode == "inline":
        # Inline mode has already finished the whole pipeline by now, and it committed
        # through its OWN session - so this `report` still holds the pre-run scalar values
        # captured by the db.refresh() above. Without re-refreshing, the response is a
        # genuinely inconsistent object: status "uploaded" and summary null, but a fully
        # populated `results` list (that relationship hadn't been loaded yet, so serializing
        # it issues a fresh post-run query while the scalar columns keep their stale
        # in-memory values). Re-fetch so the response describes one point in time.
        db.refresh(report)

    return report


@router.get("", response_model=list[ReportListItem])
def list_reports(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Report]:
    return (
        db.query(Report)
        .filter(Report.owner_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Report:
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.owner_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
