from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, func

from .database import Base


class Merchant(Base):
    __tablename__ = 'merchant'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)

class SyntheticTransaction(Base):
    __tablename__ = 'synthetic_transaction'
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    merchant_id = Column(Integer, nullable=False)
    merchant_category = Column(String, nullable=False)
    customer_type = Column(String, nullable=False)
    payment_method = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    is_fraud = Column(Boolean, nullable=False)
    is_flagged = Column(Boolean, nullable=False)
    source = Column(String, default='synthetic')
    velocity_24h = Column(Integer, default=0)
    customer_tx_count_30d = Column(Integer, default=0)
    three_ds_used = Column(Boolean, default=False)

class ModelArtifact(Base):
    __tablename__ = 'model_artifact'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    artifact_path = Column(String, nullable=False)
    metrics_json = Column(JSON, nullable=True)
    shap_top3 = Column(JSON, nullable=True)
