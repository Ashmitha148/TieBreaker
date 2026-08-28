"""
Real-time Velocity Engine API endpoints.
THE ONE MOST VALUABLE FEATURE for Razorpay Buildathon 2026 Track 2.
"""
from typing import Optional
from fastapi import APIRouter, Query

from app.services import get_velocity_engine

router = APIRouter(prefix="/velocity", tags=["Velocity Engine"])


@router.post("/score")
def compute_velocity_score(
    customer_id: str,
    amount: float,
    fingerprint: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    country_code: Optional[str] = None,
):
    """
    Compute composite velocity + device + geo risk score in real-time.
    Sub-10ms response via Redis.
    """
    engine = get_velocity_engine()
    
    if not fingerprint and user_agent and ip_address:
        fingerprint = engine.generate_device_fingerprint(
            user_agent=user_agent,
            accept_language="",
            ip_address=ip_address,
        )
    elif not fingerprint:
        fingerprint = "unknown"
    
    result = engine.compute_composite_risk(
        customer_id=customer_id,
        fingerprint=fingerprint,
        amount=amount,
        lat=lat,
        lon=lon,
        user_agent=user_agent,
        ip_address=ip_address,
        country_code=country_code,
    )
    
    return {
        "status": "success",
        "customer_id": customer_id,
        "fingerprint": fingerprint,
        "composite_risk_score": result["composite_score"],
        "risk_level": "HIGH" if result["composite_score"] > 0.7 else "MEDIUM" if result["composite_score"] > 0.3 else "LOW",
        "velocity": result["velocity"],
        "device": result["device"],
        "geo": result["geo"],
    }


@router.get("/features/{customer_id}")
def get_velocity_features(customer_id: str):
    """Get raw velocity features for a customer."""
    engine = get_velocity_engine()
    features = engine.get_velocity_features(customer_id)
    return {
        "customer_id": customer_id,
        "features": features,
    }


@router.post("/device/register")
def register_device(
    fingerprint: str,
    user_agent: str,
    ip_address: str,
    country_code: Optional[str] = None,
):
    """Register a device fingerprint and get its risk score."""
    engine = get_velocity_engine()
    risk = engine.get_device_risk_score(fingerprint)
    return {
        "fingerprint": fingerprint,
        "risk_score": risk["score"],
        "is_new": risk["is_new"],
        "is_blocked": risk["is_blocked"],
        "transaction_count": risk["transaction_count"],
    }