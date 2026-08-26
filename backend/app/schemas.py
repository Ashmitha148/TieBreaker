from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in paise (e.g. 50000 for ₹500)")
    currency: str = Field("INR", description="Currency code (default INR)")
    receipt: str | None = Field(None, description="Optional merchant receipt identifier")
    notes: dict[str, Any] | None = Field(None, description="Optional key-value metadata")


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    razorpay_order_id: str
    amount: int
    currency: str
    status: str
    receipt: str | None = None
    key_id: str | None = None
    created_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    razorpay_payment_id: str
    razorpay_order_id: str | None = None
    order_id: int | None = None
    amount: int
    currency: str
    status: str
    method: str | None = None
    bank: str | None = None
    wallet: str | None = None
    vpa: str | None = None
    email: str | None = None
    contact: str | None = None
    error_code: str | None = None
    error_description: str | None = None
    created_at: datetime


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class WebhookResponse(BaseModel):
    status: str
    message: str
    event_id: str | None = None


class ConfigResponse(BaseModel):
    is_configured: bool
    environment: str
    is_test_mode: bool
    razorpay_key_id: str | None = None