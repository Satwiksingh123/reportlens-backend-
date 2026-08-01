from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

PipelineMode = Literal["celery", "thread", "inline"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://reportlens:changeme@localhost:5432/reportlens"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # How an uploaded report's pipeline gets executed:
    #   "celery" - dispatch to a Celery worker over Redis. Production, and the only mode
    #              that survives an API restart or scales past one box.
    #   "thread" - run it on a background thread inside the API process. For local dev with
    #              no Redis/Docker: the upload still returns immediately with status
    #              "uploaded", so the client's normal poll-until-done flow works unchanged.
    #              Work is lost if the process dies mid-report - fine for dev, not for prod.
    #   "inline" - run it synchronously inside the upload request. Only for tests, where
    #              determinism beats responsiveness. In this mode the upload response blocks
    #              for the entire OCR + LLM run (tens of seconds), which looks like a hung
    #              app in a browser - that is exactly why it is not the dev default.
    pipeline_mode: PipelineMode = "celery"

    jwt_secret_key: str = "changeme-generate-a-real-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Path to a fine-tuned TrOCR model dir (from services/ocr_engine training). When unset,
    # Tesseract is used.
    ocr_model_dir: str | None = None

    # Return canned CBC text when no OCR engine is available, instead of failing the report.
    # ONLY for tests/CI on machines without the tesseract binary. It must never be on in a
    # real deployment: the canned text is a plausible-looking blood count, and serving it
    # would present fabricated medical results to a user as if they were their own.
    ocr_stub_enabled: bool = False

    upload_dir: str = "/app/uploads"
    max_upload_mb: int = 20

    # Comma-separated origins allowed to call the API from a browser (the frontend's dev
    # server and, in production, its real domain). Defaults cover Vite's default ports so
    # local frontend dev works with zero config.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
