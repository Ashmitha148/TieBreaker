
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TieBreaker"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database: Default to SQLite local fallback, ready for PostgreSQL via DATABASE_URL
    DATABASE_URL: str = "sqlite:///./tiebreaker.db"

    # Razorpay Test Mode Credentials (Never expose secrets to client)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    # ML configuration
    ML_RANDOM_SEED: int = 42
    ML_INTERNAL_TOKEN: str = ""
    GCS_ARTIFACT_BUCKET: str = ""

    # CORS Origins
    BACKEND_CORS_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i) for i in v]
        return v

    @property
    def is_razorpay_configured(self) -> bool:
        """Returns True only when real/valid Razorpay key ID and secret are configured."""
        key_id = self.RAZORPAY_KEY_ID.strip()
        key_secret = self.RAZORPAY_KEY_SECRET.strip()
        if not key_id or not key_secret:
            return False
        if key_id == "rzp_test_..." or key_secret == "...":
            return False
        return True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
REDIS_URL: str = "redis://localhost:6379/0"
