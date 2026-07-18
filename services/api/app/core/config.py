from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://reportlens:changeme@localhost:5432/reportlens"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    jwt_secret_key: str = "changeme-generate-a-real-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Path to a fine-tuned TrOCR model dir (from services/ocr_engine training). When unset
    # or unavailable, the OCR client falls back to a deterministic stub.
    ocr_model_dir: str | None = None

    upload_dir: str = "/app/uploads"
    max_upload_mb: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
