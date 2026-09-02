from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import random
import uuid
from datetime import datetime

from ..database import get_db
from ..ml.predictor import predict_transaction
from ..services.strike_selector import calculate_action_losses, threshold_baseline_decision
from ..models import Decision

router = APIRouter()


MERCHANT_PROFILES = {
    "Retail": {"avg_amount": 45000, "ltv_base": 80000, "fraud_bias": 0.05},
    "SaaS": {"avg_amount": 150000, "ltv_base": 600000, "fraud_bias": 0.02},
    "B2B": {"avg_amount": 500000, "ltv_base": 2000000, "fraud_bias": 0.03},
    "Food": {"avg_amount": 25000, "ltv_base": 40000, "fraud_bias": 0.08},
    "Travel": {"avg_amount": 350000, "ltv_base": 500000, "fraud_bias": 0.12},
    "EdTech": {"avg_amount": 120000, "ltv_base": 300000, "fraud_bias": 0.04},
}


def _generate_synthetic_record(merchant_category: str = None, force_counterintuitive: bool = False):
    if merchant_category is None:
        merchant_category = random.choice(list(MERCHANT_PROFILES.keys()))

    profile = MERCHANT_PROFILES[merchant_category]
    amount = max(1000, int(random.gauss(profile["avg_amount"], profile["avg_amount"] * 0.4)))

    # Generate realistic LTV correlated with tenure
    tenure = random.randint(7, 1500)
    ltv = int(profile["ltv_base"] * (0.5 + tenure / 2000) * random.uniform(0.8, 1.5))

    if force_counterintuitive:
        # High fraud but high LTV → REVIEW instead of BLOCK
        fraud_prob = round(random.uniform(0.68, 0.85), 2)
        fp_prob = round(random.uniform(0.25, 0.45), 2)
    else:
        fraud_prob = round(random.uniform(0.02, 0.95), 2)
        fp_prob = round(random.uniform(0.05, 0.50), 2)

    return {
        "transaction_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
        "amount": amount,
        "ltv": ltv,
        "fraud_prob": fraud_prob,
        "fp_prob": fp_prob,
        "velocity_1h": random.randint(1, 20),
        "velocity_24h": random.randint(5, 80),
        "device_change_flag": random.choice([0, 1]),
        "geo_mismatch_flag": random.choice([0, 1]),
        "is_cross_border": random.choice([0, 1]),
        "hour_of_day": random.randint(0, 23),
        "customer_tenure_days": tenure,
        "customer_tx_count_30d": random.randint(1, 120),
        "customer_refund_rate": round(random.random(), 2),
        "merchant_category": merchant_category,
        "payment_method": random.choice(["upi", "card", "netbanking", "wallet"]),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/demo/transaction")
def demo_transaction(counterintuitive: bool = False):
    """Generate a single synthetic transaction with full decision payload."""
    record = _generate_synthetic_record(force_counterintuitive=counterintuitive)
    prediction = predict_transaction(record)

    result = calculate_action_losses(
        prediction["fraud_probability"],
        prediction["fp_probability"],
        record["amount"],
        record["ltv"],
    )
    baseline = threshold_baseline_decision(prediction["fraud_probability"])

    return {
        "transaction": record,
        "prediction": prediction,
        "decision": {
            "recommended_action": result["recommended_action"],
            "baseline_action": baseline,
            "losses": result["losses"],
            "primary_reason": result["primary_reason"],
            "is_counterintuitive": result["is_counterintuitive"],
            "confidence_gap": result["confidence_gap"],
        },
        "savings_vs_baseline": _estimate_savings(result, baseline, record),
    }


@router.get("/demo/counterintuitive")
def counterintuitive_demo():
    """Return a sample counterintuitive decision where fraud is high but LTV makes REVIEW cheaper than BLOCK."""
    record = {
        "transaction_id": "DEMO-001",
        "amount": 450000,
        "ltv": 1500000,
        "fraud_prob": 0.72,
        "fp_prob": 0.35,
        "merchant_category": "B2B",
    }
    result = calculate_action_losses(0.72, 0.35, 450000, 1500000)
    baseline = threshold_baseline_decision(0.72)
    return {
        "transaction_id": "DEMO-001",
        "transaction": record,
        "fraud_prob": 0.72,
        "fp_prob": 0.35,
        "amount": 450000,
        "recommended_action": result["recommended_action"],
        "baseline_action": baseline,
        "is_counterintuitive": True,
        "explanation": "REVIEW saves more rupees than BLOCK due to high FP probability",
        "decision": {
            "recommended_action": result["recommended_action"],
            "baseline_action": baseline,
            "losses": result["losses"],
            "primary_reason": result["primary_reason"],
            "is_counterintuitive": True,
            "confidence_gap": result["confidence_gap"],
        },
        "savings_vs_baseline": _estimate_savings(result, baseline, record),
    }


@router.get("/demo/stream")
def demo_stream(count: int = 5):
    """Generate a batch of demo transactions for shadow mode simulation."""
    if count > 50:
        count = 50
    transactions = []
    for _ in range(count):
        tx = demo_transaction(counterintuitive=random.random() < 0.15)
        transactions.append(tx)
    return {"transactions": transactions, "generated_at": datetime.now().isoformat()}


@router.post("/demo/seed-decisions")
def seed_demo_decisions(db: Session = Depends(get_db), count: int = 20):
    """Pre-populate the DB with realistic demo decisions for the queue/audit pages."""
    if count > 100:
        count = 100

    created = []
    for _ in range(count):
        record = _generate_synthetic_record()
        prediction = predict_transaction(record)
        result = calculate_action_losses(
            prediction["fraud_probability"],
            prediction["fp_probability"],
            record["amount"],
            record["ltv"],
        )
        baseline = threshold_baseline_decision(prediction["fraud_probability"])

        decision = Decision(
            transaction_id=record["transaction_id"],
            fraud_prob=prediction["fraud_probability"],
            fp_prob=prediction["fp_probability"],
            amount=record["amount"],
            ltv=record["ltv"],
            recommended_action=result["recommended_action"],
            baseline_action=baseline,
            savings_vs_baseline=_estimate_savings(result, baseline, record),
            model_version="2.0.0",
            config_version="1.0",
            is_counterintuitive=result["is_counterintuitive"],
        )
        db.add(decision)
        created.append(record["transaction_id"])

    db.commit()
    return {"seeded": len(created), "transaction_ids": created}


def _estimate_savings(result, baseline_action, record):
    """Rough rupee estimate of savings vs baseline threshold system."""
    baseline_loss = result["losses"].get(baseline_action, result["losses"]["BLOCK"])
    optimal_loss = result["losses"][result["recommended_action"]]
    savings = max(0, baseline_loss - optimal_loss)
    # Add LTV salvage for counterintuitive REVIEW decisions
    if result["is_counterintuitive"] and result["recommended_action"] == "REVIEW":
        savings += record["ltv"] * 0.15
    return round(savings, 2)


@router.get("/demo/counterintuitive")
def counterintuitive_demo():
    """Return a guaranteed counterintuitive decision for demos."""
    result = calculate_action_losses(0.72, 0.35, 450000, 500000)
    baseline = threshold_baseline_decision(0.72)
    return {
        "transaction_id": "DEMO-001",
        "fraud_prob": 0.72,
        "fp_prob": 0.35,
        "amount": 450000,
        "decision": {
            "recommended_action": result["recommended_action"],
            "baseline_action": baseline,
            "is_counterintuitive": result["is_counterintuitive"],
        },
    }
