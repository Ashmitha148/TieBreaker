from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "TieBreaker"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database: Default to PostgreSQL
    DATABASE_URL: str = "postgresql+psycopg2://tiebreaker:tiebreaker@localhost:5432/tiebreaker"

    # Razorpay Test Mode Credentials (Never expose secrets to client)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API key for scoring / learning endpoints (not used on Razorpay webhooks)
    TIEBREAKER_API_KEY: str = ""

    # PII encryption key (generate with Fernet.generate_key())
    ENCRYPTION_KEY: str = ""

    # ML configuration
    ML_RANDOM_SEED: int = 42
    ML_INTERNAL_TOKEN: str = ""

    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()