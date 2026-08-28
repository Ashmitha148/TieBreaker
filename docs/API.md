# TieBreaker API Documentation

Base URL: `http://localhost:8000`
Content-Type: `application/json`
Version: 2.0.0

---

## Authentication

All endpoints require a Bearer token:

```
Authorization: Bearer <jwt_token>
```

---

## Endpoints

### 1. Create Order and Score

Creates a Razorpay order and runs the full risk scoring pipeline.

**POST /api/create-order**

Request:
```json
{
  "amount": 50000,
  "currency": "INR",
  "customer_id": "cust_123",
  "email": "user@example.com",
  "phone": "9999999999",
  "payment_method": "upi",
  "device_id": "device_abc123"
}
```

Response:
```json
{
  "order_id": "order_LxK9mN2pQr",
  "transaction_id": "pay_MnP2qR5sTu",
  "amount": 50000,
  "currency": "INR",
  "recommended_action": "REVIEW",
  "fraud_probability": 0.72,
  "fp_probability": 0.35,
  "is_counterintuitive": true,
  "velocity_flags": ["HIGH_FREQUENCY", "NEW_DEVICE"],
  "shap_explanation": {
    "amount": 0.25,
    "velocity": 0.18,
    "device": 0.15,
    "merchant": 0.12,
    "time": 0.10,
    "location": 0.08,
    "history": 0.07,
    "channel": 0.05
  },
  "expected_losses": {
    "ALLOW": 112500,
    "VERIFY": 45600,
    "REVIEW": 28400,
    "BLOCK": 67500
  },
  "model_version": "2.0.0",
  "latency_ms": 28
}
```

Actions:
- `ALLOW` — Low risk, proceed with payment
- `VERIFY` — Medium risk, send OTP/SMS verification
- `REVIEW` — High risk but high LTV, queue for analyst
- `BLOCK` — High risk, reject transaction

---

### 2. Get System Metrics

Returns real-time system performance and financial impact.

**GET /api/metrics**

Response:
```json
{
  "system_stats": {
    "total_decisions": 1247,
    "total_transactions": 5234,
    "override_rate": 3.2,
    "avg_review_time_minutes": 4.2,
    "active_models": 2,
    "queue_depth": 12
  },
  "financial_impact": {
    "fraud_loss_prevented": 2840000,
    "fp_revenue_saved": 1250000,
    "analyst_cost": 45000,
    "net_savings": 4045000
  },
  "model_performance": {
    "fraud_model": {
      "precision": 0.89,
      "recall": 0.87,
      "f1": 0.88,
      "auc_roc": 0.94,
      "samples": 45231
    },
    "fp_model": {
      "precision": 0.82,
      "recall": 0.79,
      "f1": 0.80,
      "auc_roc": 0.89,
      "samples": 28450
    }
  },
  "override_distribution": {
    "ALLOW": 35,
    "VERIFY": 25,
    "REVIEW": 30,
    "BLOCK": 10
  },
  "timestamp": "2024-01-15T14:30:00Z"
}
```

---

### 3. Get Review Queue

Returns priority-ranked transactions awaiting analyst review.

**GET /api/queue**

Query Parameters:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| limit | int | 50 | Max items to return |
| status | string | pending | Filter by status |

Response:
```json
{
  "cases": [
    {
      "transaction_id": "pay_LxK9mN2pQr",
      "amount": 45000,
      "fraud_probability": 0.72,
      "fp_probability": 0.35,
      "recommended_action": "REVIEW",
      "impact_score": 92,
      "waiting_seconds": 45,
      "velocity_flags": ["HIGH_FREQUENCY"],
      "customer_ltv": 150000,
      "created_at": "2024-01-15T14:23:01Z"
    }
  ],
  "total": 12,
  "avg_wait_seconds": 180
}
```

Impact Score Formula:
```
impact_score = (fraud_probability * 40) + 
               (amount / max_amount * 30) + 
               (ltv / max_ltv * 20) + 
               (waiting_seconds / 300 * 10)
```

---

### 4. Get Transaction Detail

Deep dive into a specific transaction with full decision trace.

**GET /api/transaction/{transaction_id}**

Response:
```json
{
  "transaction_id": "pay_LxK9mN2pQr",
  "amount": 45000,
  "currency": "INR",
  "customer_id": "cust_123",
  "fraud_probability": 0.72,
  "fp_probability": 0.35,
  "recommended_action": "REVIEW",
  "is_counterintuitive": true,
  "velocity_flags": ["HIGH_FREQUENCY", "NEW_DEVICE"],
  "shap": {
    "amount": 0.25,
    "velocity": 0.18,
    "device": 0.15,
    "merchant": 0.12,
    "time": 0.10,
    "location": 0.08,
    "history": 0.07,
    "channel": 0.05
  },
  "timeline": [
    {
      "stage": "Payment Captured",
      "timestamp": "2024-01-15T14:23:01.000Z",
      "duration_ms": 0,
      "detail": "UPI transaction initiated"
    },
    {
      "stage": "Velocity Check",
      "timestamp": "2024-01-15T14:23:01.120Z",
      "duration_ms": 120,
      "detail": "12 transactions in last hour"
    },
    {
      "stage": "Fraud Inference",
      "timestamp": "2024-01-15T14:23:01.280Z",
      "duration_ms": 160,
      "detail": "Probability: 0.72 (High Risk)"
    },
    {
      "stage": "FP Inference",
      "timestamp": "2024-01-15T14:23:01.310Z",
      "duration_ms": 30,
      "detail": "Probability: 0.35 (Medium)"
    },
    {
      "stage": "Strike Engine",
      "timestamp": "2024-01-15T14:23:01.340Z",
      "duration_ms": 30,
      "detail": "Cost-optimized: REVIEW"
    }
  ],
  "expected_losses": {
    "ALLOW": 112500,
    "VERIFY": 45600,
    "REVIEW": 28400,
    "BLOCK": 67500
  },
  "model_version": "2.0.0"
}
```

---

### 5. Submit Analyst Override

Analyst overrides the model's recommendation.

**POST /api/transaction/{transaction_id}/override**

Request:
```json
{
  "action": "ALLOW",
  "reason": "Customer verified via phone call",
  "analyst_id": "analyst_001"
}
```

Response:
```json
{
  "success": true,
  "transaction_id": "pay_LxK9mN2pQr",
  "original_action": "REVIEW",
  "override_action": "ALLOW",
  "analyst_id": "analyst_001",
  "timestamp": "2024-01-15T14:35:00Z"
}
```

---

### 6. Get Audit Trail

Returns full decision and override history.

**GET /api/audit**

Query Parameters:
| Param | Type | Description |
|-------|------|-------------|
| start_date | ISO date | Filter from date |
| end_date | ISO date | Filter to date |
| action | string | Filter by action type |
| analyst_id | string | Filter by analyst |

Response:
```json
{
  "logs": [
    {
      "id": "audit_001",
      "timestamp": "2024-01-15T14:23:01Z",
      "transaction_id": "pay_LxK9mN2pQr",
      "action": "DECISION_REVIEW",
      "analyst_id": null,
      "reason": null,
      "model_version": "2.0.0"
    },
    {
      "id": "audit_002",
      "timestamp": "2024-01-15T14:35:00Z",
      "transaction_id": "pay_LxK9mN2pQr",
      "action": "OVERRIDE_ALLOW",
      "analyst_id": "analyst_001",
      "reason": "Customer verified via phone call",
      "model_version": "2.0.0"
    }
  ],
  "total": 1247,
  "page": 1,
  "per_page": 50
}
```

---

### 7. Get Learning Insights

Returns before/after metrics showing model improvement from overrides.

**GET /api/insights**

Response:
```json
{
  "before": {
    "accuracy": 0.82,
    "precision": 0.79,
    "recall": 0.74,
    "f1": 0.76,
    "samples": 10000
  },
  "after": {
    "accuracy": 0.91,
    "precision": 0.89,
    "recall": 0.87,
    "f1": 0.88,
    "samples": 15000
  },
  "learning_curve": [
    { "day": "D1", "accuracy": 0.76, "precision": 0.74, "samples": 100 },
    { "day": "D2", "accuracy": 0.77, "precision": 0.75, "samples": 250 }
  ],
  "override_stats": {
    "total_overrides": 142,
    "override_by_action": {
      "ALLOW": 45,
      "BLOCK": 32,
      "REVIEW": 38,
      "VERIFY": 27
    },
    "override_accuracy": 0.84
  }
}
```

---

### 8. Get / Update Configuration

System parameter tuning.

**GET /api/config**

Response:
```json
{
  "fraud_threshold": 0.72,
  "fp_threshold": 0.35,
  "review_cost": 100,
  "fraud_multiplier": 2.5,
  "ltv_weight": 0.15,
  "model_version": "2.0.0",
  "last_updated": "2024-01-15T10:00:00Z",
  "updated_by": "admin"
}
```

**POST /api/config**

Request:
```json
{
  "fraud_threshold": 0.75,
  "fp_threshold": 0.30,
  "review_cost": 120
}
```

Response:
```json
{
  "success": true,
  "changes": {
    "fraud_threshold": { "old": 0.72, "new": 0.75 },
    "fp_threshold": { "old": 0.35, "new": 0.30 },
    "review_cost": { "old": 100, "new": 120 }
  },
  "timestamp": "2024-01-15T14:40:00Z"
}
```

---

## Error Codes

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Bad Request | Invalid amount format |
| 401 | Unauthorized | Missing/invalid JWT |
| 404 | Not Found | Transaction not found |
| 429 | Rate Limited | >100 req/min |
| 500 | Server Error | Model inference failed |

---

## Webhooks

TieBreaker can send webhooks to your endpoint.

### Decision Webhook

```json
{
  "event": "transaction.decision",
  "transaction_id": "pay_MnP2qR5sTu",
  "decision": "REVIEW",
  "fraud_probability": 0.72,
  "timestamp": "2024-01-15T14:23:01Z"
}
```

### Override Webhook

```json
{
  "event": "transaction.override",
  "transaction_id": "pay_MnP2qR5sTu",
  "original_decision": "REVIEW",
  "override_decision": "ALLOW",
  "analyst_id": "analyst_001",
  "timestamp": "2024-01-15T14:35:00Z"
}
```

---

API version 2.0.0 — Razorpay Buildathon 2026
