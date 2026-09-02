from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "TieBreaker"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on", "t", "debug")
        return bool(v)
    DATABASE_URL: str = "sqlite:///./tiebreaker.db"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    TIEBREAKER_API_KEY: str = ""
    ENCRYPTION_KEY: str = ""
    ML_RANDOM_SEED: int = 42
    ML_INTERNAL_TOKEN: str = ""

    def get_cors_origins(self) -> list[str]:
        raw = os.getenv("BACKEND_CORS_ORIGINS", "[\"*\"]")
        v = raw.strip()
        if not v:
            return ["*"]
        if v.startswith("[") and v.endswith("]"):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return [x.strip() for x in v.split(",") if x.strip()]

    @property
    def is_razorpay_configured(self) -> bool:
        return bool(self.RAZORPAY_KEY_ID and self.RAZORPAY_KEY_SECRET)

    @property
    def is_webhook_secret_configured(self) -> bool:
        return bool(self.RAZORPAY_WEBHOOK_SECRET)


settings = Settings()
