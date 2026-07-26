from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# In eager mode the task runs inline and its return value comes straight back, so no
# broker or result backend is involved. Configuring them anyway makes Celery import the
# redis transport/backend modules at call time - which hard-fails when redis isn't
# installed, defeating the point of a broker-free local run. Leave both unset instead.
_eager = settings.celery_task_always_eager

celery_app = Celery(
    "reportlens",
    broker=None if _eager else settings.celery_broker_url,
    backend=None if _eager else settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    # Local/dev escape hatch: run tasks in-process instead of needing Redis + a worker.
    # Off by default; see Settings.celery_task_always_eager.
    task_always_eager=_eager,
    task_eager_propagates=_eager,
)

# ensure tasks are registered
from app.tasks import pipeline  # noqa: E402,F401
