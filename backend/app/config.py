from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "TieBreaker"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+psycopg2://tiebreaker:tiebreaker@localhost:5432/tiebreaker"
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
