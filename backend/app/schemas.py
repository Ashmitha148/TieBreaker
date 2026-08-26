from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class OrderCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in paise (e.g. 50000 for ₹500)")
    currency: str = Field("INR", description="Currency code (default INR)")
    receipt: Optional[str] = Field(None, description="Optional merchant receipt identifier")
    notes: Optional[Dict[str, Any]] = Field(None, description="Optional key-value metadata")


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    razorpay_order_id: str
    amount: int
    currency: str
    status: str
    receipt: Optional[str] = None
    key_id: Optional[str] = None
    created_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    razorpay_payment_id: str
    razorpay_order_id: Optional[str] = None
    order_id: Optional[int] = None
    amount: int
    currency: str
    status: str
    method: Optional[str] = None
    bank: Optional[str] = None
    wallet: Optional[str] = None
    vpa: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    created_at: datetime


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class WebhookResponse(BaseModel):
    status: str
    message: str
    event_id: Optional[str] = None


class ConfigResponse(BaseModel):
    is_configured: bool
    environment: str
    is_test_mode: bool
    razorpay_key_id: Optional[str] = None