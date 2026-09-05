# TieBreaker Architecture

System design document for Razorpay Buildathon 2026, Track 2 — built solo by [Ashmitha148](https://github.com/Ashmitha148).

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
    |    (GBClassifier) (GBClassifier) (Heuristic)
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

**Algorithm**: `xgboost.XGBClassifier`, isotonic-calibrated via `sklearn.calibration.CalibratedClassifierCV` (see `app/ml/train_models.py`, "V6 — honest temporal CV")
**Features**: curated, leakage-safe feature set — past-only temporal aggregations plus a documented subset of IEEE-CIS `V`/`C`/`D`/`dist1`/`id` columns and an engineered `M`-match-count feature (`FRAUD_FEATURES` in `app/ml/data.py`)

**Training data**: the real **IEEE-CIS Fraud Detection dataset** (Kaggle) — 300k-row temporal head, 70/15/15 train/val/holdout split, sorted chronologically before splitting so the holdout is always chronologically after training data. A `leakage_check()` runs automatically before any model is trusted, and `ml/evaluation.py` explicitly flags any model scoring above 0.98 ROC-AUC with >95% precision as probable leakage or overfitting — this caught real leakage in an earlier version (see the "V2 → V3" fix note in `app/ml/data.py`).

**Measured performance** (holdout, never touched during tuning): precision 0.805, recall 0.996, F1 0.891, PR-AUC 0.995, ROC-AUC 0.9999, Brier 0.0023. Full metrics are served at `GET /api/metrics/model-performance`. If a trained artifact is missing at runtime, `ModelManager` falls back to a heuristic scorer rather than failing the request — see [Current Limitations](#11-current-limitations).

### 3.3 False Positive Model

Traditional fraud models maximize fraud detection. They don't explicitly learn what a false positive looks like — TieBreaker trains a second, independent XGBoost classifier for exactly that: P(this transaction is legitimate but scores as risky).

**Algorithm**: `xgboost.XGBClassifier` (separate model instance, separate feature set, same IEEE-CIS temporal pipeline as the fraud model)
**Features**: a subset of `FP_FEATURES` in `app/ml/data.py` — amount, tenure/velocity aggregates, device and geo mismatch flags
**Output**: P(FalsePositive | transaction)
**Measured performance** (holdout): precision 0.937, recall 0.996, F1 0.966, PR-AUC 0.971, ROC-AUC 0.988, Brier 0.0038.

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
   - Runs Velocity Engine, Fraud Model, FP Model, LTV Estimator, Strike Decision Engine
   - Returns: {order_id, decision, explanation}
4. Frontend shows decision + pipeline animation
5. If REVIEW/BLOCK: Add to analyst queue
6. If ALLOW: Proceed to Razorpay checkout

**Total latency**: see [§6 Performance](#6-performance) for measured numbers and their caveats — the per-step breakdown above is not individually instrumented, so no sub-step timings are claimed.

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

### Latency

Measured end-to-end on `POST /api/transactions` (50 requests, in-process `TestClient`, SQLite, Redis unavailable so the velocity engine takes its zero-fallback path):

| Metric | Value |
|--------|-------|
| Median | ~7ms |
| p95 | ~8ms |

This is a floor, not a production number: it excludes network round-trip, a real Postgres connection, and a live Redis lookup, all of which add latency in a deployed environment. It has not been measured against the deployed Vercel/production backend. Re-measure against the real deployment before quoting a latency SLA externally.

### Throughput

Not load-tested. The numbers below are estimates based on the measured per-request latency, not a benchmark run — treat them as a starting assumption to validate, not a capacity guarantee.

- Single FastAPI worker: ~400 RPS (estimated)
- With 4 workers + Redis caching: ~1,500 RPS (estimated)
- Horizontal scaling: Add workers behind a load balancer

### Caching

- **Redis**: Velocity counters (1-hour TTL), LTV estimates (24-hour TTL)
- **In-memory**: Model warm-up, feature transformers
- **No caching for**: Model inference (must be real-time)

---

## 7. Security

- **API authentication**: static API key via `X-API-Key` header (`app/auth.py`), required on scoring and mutating endpoints. Not JWT — see Current Limitations.
- **Rate limiting**: 100 req/min per API key on `/api/transactions`, 20 req/min on `/api/what-if` (`slowapi`, keyed by API key with IP fallback).
- **Webhook verification**: Razorpay webhook signatures are verified fail-closed — a missing or empty `RAZORPAY_WEBHOOK_SECRET` returns 401, it does not silently accept the request.
- **CORS**: locked to the exact production frontend origin in production; wildcard/localhost origins are rejected and overridden.
- **Audit immutability**: Audit logs are append-only, no UPDATE/DELETE.
- **Model versioning**: Every decision tagged with model version.

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

Ideas under consideration, not committed or scheduled:

- Automatic retraining pipeline triggered off analyst override volume (the `/api/learning/trigger-retrain` endpoint currently only reports whether retraining looks warranted — it does not retrain)
- Alembic-based Postgres migration path for production (see Current Limitations)
- JWT-based auth to replace the current static API key

---

## 11. Current Limitations

This section exists so the rest of the document isn't read as a claim of production-grade completeness. Known gaps, honestly:

- **Real but Kaggle-sourced training data, not live merchant traffic.** Both models are trained on the real IEEE-CIS Kaggle fraud dataset with a leakage-checked temporal split (see §3.2–3.3) — this is genuine fraud-labeled data, but it is not TieBreaker's own merchants' transactions, chargebacks, or reports, so performance on live traffic is unvalidated.
- **Heuristic fallbacks, not just the review-time model.** If a trained `.joblib` artifact is missing for the fraud model, FP model, or review-time model, `ModelManager` falls back to a hand-written scoring heuristic (see `app/ml/models.py`) rather than failing the request. This keeps the API up but means decisions can silently be heuristic-quality rather than model-quality; `GET /health` surfaces this via `ml.fraud_model_loaded` / `ml.fp_model_loaded`. Note: `xgboost` must be installed for the real models to load — see Deployment guide.
- **No JWT.** API authentication is a single static API key (`X-API-Key`, `app/auth.py`), not JWT, OAuth, or per-user identity. There's no token expiry or per-user revocation.
- **No automatic retraining.** `POST /api/learning/trigger-retrain` reports whether override volume suggests retraining is warranted; it does not retrain, deploy, or A/B test a new model. Any retraining today is a manual run of `train_models.py`.
- **SQLite by default.** Production deployments should set `DATABASE_URL` to Postgres; SQLite remains the default and is what CI/tests run against.

---

Built for Razorpay Buildathon 2026.