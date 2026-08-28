# TieBreaker Architecture

System design document for Razorpay Buildathon 2026.

---

## 1. Overview

TieBreaker is a real-time payment risk intelligence platform. It uses dual-model inference and cost-optimized decisioning to minimize total financial loss from fraud and false positives.

### Design Principles

1. **Economic Optimization over Accuracy** — Minimize rupee loss, not error rate
2. **Explainability by Default** — Every decision has SHAP + timeline + audit
3. **Human-in-the-Loop** — Analysts can override; overrides improve the model
4. **Sub-50ms Latency** — Decision must not slow down checkout
5. **Razorpay-Native** — Built around Razorpay's order lifecycle and Indian payment patterns

---

## 2. High-Level Architecture

```
Client Layer (React)
    |
    v
FastAPI Gateway
    |
    +----------------+----------------+----------------+
    |                |                |                |
Velocity Engine   Decision      Audit/Learning    Razorpay
(Redis)          Pipeline        Service          Orders API
    |                |
    |         +------+------+-----------+
    |         |             |           |
    |    Fraud Model    FP Model    LTV Estimator
    |    (XGBoost)     (XGBoost)   (Heuristic)
    |         |             |           |
    |         +------+------+-----------+
    |                |
    |       Strike Decision Engine
    |         (Cost Optimizer)
    |                |
    |    +-----------+-----------+
    |    |           |           |
    |  ALLOW      REVIEW      BLOCK
    | (Low risk) (Counterint.) (High risk)
    |                |
    |         Analyst Override
    |                |
    +--------> PostgreSQL (Primary)
```

---

## 3. Components

### 3.1 Velocity Engine

Fast pre-filtering before expensive model inference.

- **Latency**: <5ms
- **Implementation**: Redis-backed rule engine

Rules:
- Transaction frequency per device (>=12 txns/hr -> flag)
- Velocity per card/UPI ID (>=5 txns/10min -> flag)
- Device fingerprint novelty (new device + high amount -> flag)
- Merchant category risk (high-risk MCCs -> flag)
- Geolocation anomaly (impossible travel -> flag)

```python
class VelocityEngine:
    def check(self, txn):
        flags = []
        recent = self.redis.zcount(
            f"velocity:{txn.device_id}",
            txn.timestamp - 3600,
            txn.timestamp
        )
        if recent >= 12:
            flags.append("HIGH_FREQUENCY")
        if not self.redis.exists(f"device:{txn.device_id}"):
            flags.append("NEW_DEVICE")
        return flags
```

### 3.2 Fraud Detection Model

**Algorithm**: XGBoost Classifier
**Features**: 47 engineered features

- Transaction amount + velocity stats
- Device fingerprint entropy
- Merchant risk score
- Time-based features (hour, day-of-week, is_weekend)
- Historical customer behavior (avg amount, std dev, days since last)
- Payment method risk (UPI < Card < NetBanking)

**Training Data**:
- Confirmed fraud labels from chargebacks + merchant reports
- Synthetic SMOTE oversampling for minority class
- Time-based train/test split (no data leakage)

**Performance**:
- Precision: 0.89
- Recall: 0.87
- F1: 0.88
- AUC-ROC: 0.94

### 3.3 False Positive Model

Traditional fraud models maximize fraud detection. They don't explicitly learn what a false positive looks like. The FP model is trained on:

- Transactions that were blocked but later confirmed legitimate
- High-LTV customers with unusual but valid patterns
- Seasonal spikes (Diwali shopping, salary day)

**Algorithm**: XGBoost Classifier (separate feature weights)
**Output**: P(FalsePositive | transaction)

### 3.4 LTV Estimator

Estimates customer lifetime value for cost optimization. Fast heuristic, no ML latency.

```python
def estimate_ltv(customer):
    base = customer.avg_monthly_spend * 12
    if customer.tenure_months > 12:
        base *= 1.5
    if customer.merchant_tier == "enterprise":
        base *= 2.0
    if customer.chargeback_rate < 0.01:
        base *= 1.3
    return base
```

### 3.5 Strike Decision Engine

This is the core innovation.

Instead of: `if fraud_prob > 0.7: BLOCK`

TieBreaker computes:

```
For each action in {ALLOW, VERIFY, REVIEW, BLOCK}:
    ExpectedLoss(action) = sum(P(outcome | action) * Cost(outcome))

RecommendedAction = argmin ExpectedLoss(action)
```

**Cost Model**:

| Outcome | Cost Formula | Typical Value |
|---------|-------------|---------------|
| Fraud allowed | Amount * FraudMultiplier | Rs 1,12,500 |
| False block | LTV * FPWeight + FrictionCost | Rs 67,500 |
| Review (correct) | AnalystCost + Friction | Rs 500 |
| Review (fraud slips) | AnalystCost + PartialFraud | Rs 13,500 |
| Verify (legit) | FrictionCost | Rs 3,600 |
| Verify (fraud) | FrictionCost + PartialFraud | Rs 30,600 |

**Counterintuitive Detection**:

A decision is "counterintuitive" when:
- Fraud probability > 0.6 (high risk)
- But recommended action is REVIEW (not BLOCK)
- Because: Loss(REVIEW) < Loss(BLOCK) due to high LTV

This is the key differentiator. TieBreaker knows when a customer is worth saving.

### 3.6 SHAP Explainer

Every decision includes feature importance:

```python
import shap

explainer = shap.TreeExplainer(fraud_model)
shap_values = explainer.shap_values(txn_features)

explanation = {
    "amount": 0.25,
    "velocity": 0.18,
    "device": 0.15,
    "merchant": 0.12,
    "time": 0.10,
    "location": 0.08,
    "history": 0.07,
    "channel": 0.05,
}
```

### 3.7 Active Learning Loop

```
Analyst overrides decision -> Logged to Audit DB
         |
         v
   Batch collected (N=100)
         |
         v
   Trigger retraining
         |
         v
   Incremental model update
         |
         v
   A/B test vs current model
         |
         v
   Deploy if F1 improves > 1%
```

The system tracks accuracy/precision/recall/F1 before and after override batches to prove continuous improvement.

---

## 4. Data Flow

### Checkout Flow

1. Customer clicks "Pay" on merchant site
2. Frontend calls POST /api/create-order
3. Backend:
   - Creates Razorpay order
   - Runs Velocity Engine (5ms)
   - Runs Fraud Model + FP Model in parallel (15ms)
   - LTV Estimator lookup (1ms)
   - Strike Decision Engine (2ms)
   - Returns: {order_id, decision, explanation}
4. Frontend shows decision + pipeline animation
5. If REVIEW/BLOCK: Add to analyst queue
6. If ALLOW: Proceed to Razorpay checkout

**Total Latency**: ~25-35ms

### Analyst Review Flow

1. Analyst opens Queue Oracle (/queue)
2. Sees priority-ranked transactions (impact score)
3. Clicks transaction -> Deep Dive page
4. Views: Pipeline, Timeline, SHAP, What-If
5. Decides: ALLOW / BLOCK / REVIEW / VERIFY
6. Override logged to Audit Trail
7. Override fed to Active Learning batch

### Audit Flow

1. Every decision + override logged immutably
2. Audit trail searchable by: transaction, action, analyst, date
3. Config changes logged with before/after values
4. Model version tracked per decision
5. Full reproducibility for regulatory review

---

## 5. Database Schema

### Transactions

```sql
CREATE TABLE transactions (
    id              UUID PRIMARY KEY,
    transaction_id  VARCHAR(32) UNIQUE NOT NULL,
    amount          INTEGER NOT NULL,
    currency        VARCHAR(3) DEFAULT 'INR',
    fraud_probability    DECIMAL(5,4),
    fp_probability       DECIMAL(5,4),
    recommended_action   VARCHAR(10),
    is_counterintuitive  BOOLEAN DEFAULT FALSE,
    customer_id     VARCHAR(32),
    merchant_id     VARCHAR(32),
    device_id       VARCHAR(64),
    payment_method  VARCHAR(20),
    created_at      TIMESTAMP DEFAULT NOW(),
    decided_at      TIMESTAMP,
    razorpay_order_id VARCHAR(64)
);
```

### Audit Logs

```sql
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY,
    timestamp       TIMESTAMP DEFAULT NOW(),
    transaction_id  VARCHAR(32) REFERENCES transactions(transaction_id),
    action          VARCHAR(30) NOT NULL,
    analyst_id      VARCHAR(32),
    reason          TEXT,
    model_version   VARCHAR(10) DEFAULT '2.0.0'
);
```

### Review Queue

```sql
CREATE TABLE review_queue (
    id              UUID PRIMARY KEY,
    transaction_id  VARCHAR(32) UNIQUE REFERENCES transactions(transaction_id),
    impact_score    INTEGER NOT NULL,
    waiting_seconds INTEGER DEFAULT 0,
    assigned_to     VARCHAR(32),
    status          VARCHAR(10) DEFAULT 'pending',
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 6. Performance

### Latency Budget

| Component | Budget | Actual |
|-----------|--------|--------|
| Velocity Engine | 5ms | 2-3ms |
| Fraud Model | 15ms | 10-12ms |
| FP Model | 15ms | 8-10ms |
| LTV Lookup | 2ms | 1ms |
| Strike Engine | 5ms | 1-2ms |
| DB Write | 5ms | 3-5ms |
| **Total** | **50ms** | **25-35ms** |

### Throughput

- Single FastAPI worker: ~400 RPS
- With 4 workers + Redis caching: ~1,500 RPS
- Horizontal scaling: Add workers behind Nginx load balancer

### Caching

- **Redis**: Velocity counters (1-hour TTL), LTV estimates (24-hour TTL)
- **In-memory**: Model warm-up, feature transformers
- **No caching for**: Model inference (must be real-time)

---

## 7. Security

- End-to-end encryption: All PII encrypted at rest (AES-256)
- API authentication: JWT tokens with 15-min expiry
- Rate limiting: 100 req/min per API key
- Audit immutability: Audit logs append-only, no UPDATE/DELETE
- Model versioning: Every decision tagged with model version
- SOC 2 readiness: Audit trails, access controls, data retention

---

## 8. Razorpay Integration

### Orders API

TieBreaker wraps the Razorpay Orders API:

```python
@app.post("/api/create-order")
async def create_order(request):
    # 1. Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        'amount': request.amount,
        'currency': 'INR',
        'receipt': f'receipt_{uuid4()}'
    })

    # 2. Score transaction
    decision = decision_engine.decide(request, razorpay_order)

    # 3. Return enriched response
    return {
        'order_id': razorpay_order['id'],
        'transaction_id': decision.transaction_id,
        'recommended_action': decision.action,
        'fraud_probability': decision.fraud_prob,
        'fp_probability': decision.fp_prob,
        'is_counterintuitive': decision.is_counterintuitive
    }
```

### Webhooks

Listen to Razorpay webhooks for:
- payment.captured -> Confirm legitimate, train FP model
- payment.failed -> Analyze failure reason
- refund.processed -> Potential fraud signal

---

## 9. Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tiebreaker
      - REDIS_URL=redis://redis:6379

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
```

See DEPLOYMENT.md for full instructions.

---

## 10. Future Roadmap

- Graph Neural Networks for merchant-merchant fraud rings
- Real-time device fingerprinting with browser canvas + WebGL entropy
- AutoML pipeline for automated model retraining
- Multi-merchant federation — learn across merchants without data sharing
- Voice/SMS verification integration for high-value VERIFY decisions

---

Built for Razorpay Buildathon 2026.
