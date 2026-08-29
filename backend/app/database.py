from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings

# Engine configuration: PostgreSQL-ready, with SQLite local fallback support
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    # Railway and Heroku often provide postgres:// instead of postgresql://
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine_kwargs = {}
if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production PostgreSQL pool configuration
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_decision_columns() -> None:
    """create_all does not add columns to an existing SQLite table."""
    if not db_url.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "decisions" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("decisions")}
    needed = {
        "merchant_category": "VARCHAR(50)",
        "feature_snapshot": "TEXT",
        "is_counterintuitive": "BOOLEAN DEFAULT 0",
        "baseline_action": "VARCHAR(20) DEFAULT 'BLOCK'",
        "savings_vs_baseline": "FLOAT DEFAULT 0",
        "model_version": "VARCHAR(64) DEFAULT 'unloaded'",
        "config_version": "VARCHAR(20) DEFAULT '1.0'",
    }
    with engine.begin() as conn:
        for name, ddl in needed.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE decisions ADD COLUMN {name} {ddl}"))
