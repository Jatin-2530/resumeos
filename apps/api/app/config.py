from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root regardless of CWD
_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # App
    app_name: str = "ResumeOS API"
    python_env: str = "development"
    log_level: str = "INFO"
    api_secret_key: str = "change-me-in-production-must-be-32-chars"
    allowed_origins: str = "http://localhost:3000"

    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    # Gemini AI
    gemini_api_key: str
    gemini_flash_model: str = "gemini-2.5-flash-preview-05-20"
    gemini_pro_model: str = "gemini-2.5-pro-preview-05-06"

    # Storage
    supabase_storage_bucket: str = "resumes"
    max_upload_size_mb: int = 10
    allowed_file_types: str = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/pdf"
    )

    # LibreOffice
    libreoffice_path: str = "/usr/bin/libreoffice"
    render_temp_dir: str = "/tmp/resumeos"

    # Rate limiting
    rate_limit_requests_per_minute: int = 30
    rate_limit_upload_per_hour: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Feature flags
    enable_ats_validation: bool = True
    enable_recruiter_simulation: bool = True
    enable_libreoffice_rendering: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.python_env == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_mime_types(self) -> list[str]:
        return [t.strip() for t in self.allowed_file_types.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
