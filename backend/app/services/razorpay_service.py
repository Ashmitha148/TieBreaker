import hashlib
import hmac
from typing import Any
from uuid import uuid4

import razorpay

from ..config import settings


class RazorpayNotConfiguredError(Exception):
    """Raised when Razorpay operations are invoked without configured credentials."""


def get_razorpay_client() -> razorpay.Client:
    """
    Initializes and returns the official Razorpay client using server-side credentials.
    Raises RazorpayNotConfiguredError if credentials are not configured.
    """
    if not settings.is_razorpay_configured:
        raise RazorpayNotConfiguredError(
            "Razorpay Test Mode credentials are not configured. "
            "Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env."
        )
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_order(
    amount: int,
    currency: str = "INR",
    receipt: str | None = None,
    notes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Creates a real Razorpay Test Mode order via the Razorpay API.
    Amount must be specified in the smallest currency unit (paise for INR).
    """
    client = get_razorpay_client()
    payload = {
        "amount": amount,
        "currency": currency,
        "receipt": receipt or f"rcpt_{uuid4().hex[:12]}",
    }
    if notes:
        payload["notes"] = notes

    order_data = client.order.create(data=payload)
    return order_data


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """
    Verifies the X-Razorpay-Signature HMAC-SHA256 signature using the raw request body.
    Constant-time comparison is used to prevent timing attacks.
    """
    if not secret or not signature or not raw_body:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    secret: str,
) -> bool:
    """
    Verifies the client checkout response signature (razorpay_order_id|razorpay_payment_id).
    """
    if not secret or not razorpay_signature or not razorpay_order_id or not razorpay_payment_id:
        return False

    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, razorpay_signature)