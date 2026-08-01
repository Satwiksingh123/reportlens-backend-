from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# Only the "celery" pipeline mode actually talks to a broker. In the other modes the task
# body is invoked directly (see app.tasks.dispatch), so pointing Celery at a broker/result
# backend it will never use is worse than useless: Celery imports the redis transport and
# backend modules on first use, which hard-fails when redis isn't installed - the exact
# situation those modes exist to support. Leave both unset there.
_uses_broker = settings.pipeline_mode == "celery"

celery_app = Celery(
    "reportlens",
    broker=settings.celery_broker_url if _uses_broker else None,
    backend=settings.celery_result_backend if _uses_broker else None,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)

# ensure tasks are registered
from app.tasks import pipeline  # noqa: E402,F401
