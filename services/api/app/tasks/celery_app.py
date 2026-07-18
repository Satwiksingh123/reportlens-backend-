from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reportlens",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)

# ensure tasks are registered
from app.tasks import pipeline  # noqa: E402,F401
