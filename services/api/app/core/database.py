from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")

# SQLite needs explicit help to be used the way this app uses a database:
#   check_same_thread=False - the pipeline can run on a background thread (PIPELINE_MODE
#     "thread"), and pysqlite otherwise refuses a connection created on another thread.
#   timeout - wait for a competing writer instead of raising "database is locked"
#     immediately; the pipeline holds brief write transactions while the API serves polls.
_connect_args = {"check_same_thread": False, "timeout": 30} if _is_sqlite else {}

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):
        """WAL lets the API keep reading while the pipeline writes - without it, polling for
        report status during processing can block or fail with 'database is locked'."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
