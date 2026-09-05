# TieBreaker — API Reference

Base URL (local): `http://localhost:8000`
Base URL (production): the Railway backend URL behind `https://tie-breaker-pi.vercel.app`
Content-Type: `application/json` unless noted.

This document only lists endpoints that exist in `backend/app/routes/` today. Every request/response shape below is taken directly from the Pydantic models and route handlers, not reconstructed from memory — if you change a route, update this file in the same PR, or it'll rot exactly like the version this replaced.

---

## Authentication

Most mutating and scoring endpoints require:

```
X-API-Key: <your key>
```

- **Required in production** (`ENVIRONMENT=production`) — the app refuses to start serving these routes unauthenticated.
- **No-op in local/dev** if `TIEBREAKER_API_KEY` is unset — useful for `pytest` and local hacking, don't rely on it for anything real.
- Not JWT, not OAuth. One shared key, no expiry, no per-user identity.

Endpoints that do **not** require `X-API-Key`: `GET /`, `GET /health`, `GET /api/config` (read), `POST /api/payment/create-order`, `POST /api/payment/verify`, and `POST /api/webhooks/razorpay` (authenticated via Razorpay HMAC signature).

Rate limits (keyed by API key, IP fallback): **100/min** on `POST /api/transactions`, **20/min** on `POST /api/what-if`.

---

## Health & root

**GET /** → service identity, no auth.
```json
{"status": "ready", "project": "TieBreaker", "service": "tiebreaker", "version": "2.0.0", "phase": "production"}
```

**GET /health** → composite health, no auth. `status` is `"degraded"` if ML artifacts failed to load *or* Redis is unreachable — check this before a demo.
```json
{
  "status": "ok",
  "version": "2.0.0",
  "environment": "development",
  "ml": {"fraud_model_loaded": true, "fp_model_loaded": true, "fraud_metrics": {}, "fp_metrics": {}},
  "velocity_engine": {"redis_connected": true},
  "degraded_reasons": []
}
```

---

## Risk decisioning (the Strike Decision Engine)

### POST /api/transactions
Scores a transaction through the full cost-optimizing engine. **Requires `X-API-Key`.** 100/min.

Request (`TransactionRequest`):
```json
{
  "transaction_id": "TXN-001",
  "customer_id": "cust_123",
  "amount": 45000,
  "ltv": 300000,
  "merchant_category": "Retail",
  "device_change_flag": 0,
  "geo_mismatch_flag": 0,
  "is_cross_border": 0,
  "hour_of_day": 14,
  "customer_tenure_days": 365,
  "customer_tx_count_30d": 10,
  "customer_refund_rate": 0.0,
  "payment_method": "upi",
  "device_id": "device_abc"
}
```
`transaction_id` must be unique — re-submitting one returns **409**. Velocity (`velocity_1h`/`velocity_24h`) is looked up from Redis server-side, not supplied by the caller.

Response:
```json
{
  "transaction_id": "TXN-001",
  "recommended_action": "REVIEW",
  "baseline_action": "BLOCK",
  "fraud_probability": 0.72,
  "fp_probability": 0.35,
  "savings_vs_baseline": 39100.0,
  "is_counterintuitive": true,
  "velocity": {"velocity_1h": 2, "velocity_24h": 5, "device_tx_count_1h": 1, "source": "redis"},
  "velocity_source": "redis",
  "model_version": "xgb-v6"
}
```

### GET /api/transactions
Last 100 decisions (most recent first). **Requires `X-API-Key`.** Seeds one demo row if the table is empty.

### GET /api/transactions/{transaction_id}
Full detail: losses for all four actions, SHAP drivers, override info if any. **Requires `X-API-Key`.**

### POST /api/transactions/{transaction_id}/override
Analyst override. **Requires `X-API-Key`.**
```json
{"action": "ALLOW", "reason": "Customer verified via phone call", "analyst_id": "analyst_001"}
```
`action` must be one of `ALLOW`/`VERIFY`/`REVIEW`/`BLOCK` or **400**. Unknown transaction → **404**.

### GET /api/transactions/{transaction_id}/shap-chart
Server-rendered SHAP waterfall plot for the transaction's stored feature snapshot. **Requires `X-API-Key`.** Returns `{"transaction_id", "chart_base64", "format": "png"}`.

### POST /api/what-if
Simulate a decision without persisting anything — for demos, analyst training, or sensitivity checks. **Requires `X-API-Key`.** 20/min.

Same feature fields as `TransactionRequest` (minus `transaction_id`/`customer_id`), plus optional `override_fraud_prob` / `override_fp_prob` (each 0–1) to bypass live model inference for either side independently. Response includes `model_inference`, `decision`, `financial_analysis` (losses for all four actions + savings), and `parameter_sensitivity` (how the decision shifts under ±20% LTV/amount).

---

## Orders, payments & Razorpay integration

### POST /api/create-order

Legacy alias for the Razorpay order creation endpoint. Prefer `POST /api/payment/create-order` for new integrations.
```json
{"amount": 50000, "currency": "INR", "receipt": "rcpt_1", "notes": {}}
```
`amount` is in paise. Injects `notes.requires_3ds = "true"` when `fraud_probability > 0.7`. Returns `order_id`, `recommended_action`, `fraud_prob`, `fp_prob`, `requires_3ds`, `key_id`.

### GET /api/orders
All orders, no auth.

### POST /api/payment/create-order
What the live `/checkout` demo page actually calls. Requires Razorpay credentials configured server-side (**503** otherwise). Returns `order_id`, `amount`, `currency`, `key_id` for the Razorpay Checkout.js modal.

### POST /api/payment/verify
Verifies the Checkout.js response signature (`HMAC-SHA256("order_id|payment_id")`) — **mandatory**, returns **400** on mismatch — then re-runs the threshold decision and persists a `Payment` + `Decision`.
```json
{"razorpay_order_id": "order_xxx", "razorpay_payment_id": "pay_xxx", "razorpay_signature": "..."}
```

### GET /api/payments
Query params: `status`, `method`, `limit` (default 50, max 200). No auth.

---

## Webhooks

### POST /api/webhooks/razorpay
Receives Razorpay webhook deliveries. Verified via `X-Razorpay-Signature` (HMAC-SHA256 of the raw body against `RAZORPAY_WEBHOOK_SECRET`) — missing secret or bad signature → **400**. Deduplicated on `X-Razorpay-Event-Id` (idempotent replay). Processing (updating `Payment`/`Order`/`Decision.outcome` for `payment.captured`, `payment.authorized`, `payment.failed`, `refund.processed`, `order.paid`) happens as a background task after a `202`-style accept.

### GET /api/webhooks
Paginated (`skip`, `limit`) webhook event log. **Requires `X-API-Key`.**

### GET /api/webhooks/{event_id}
Single event detail. **Requires `X-API-Key`.** **404** if unknown.

---

## Queue

### GET /api/queue
Priority-ranked review queue. Query params: `limit` (default 50), `min_fraud_prob`. No auth. If the `decisions` table is empty, returns synthetic demo cases (clearly tagged `"source": "demo"` in the response) so the UI has something to render before real traffic exists; otherwise `"source": "database"`. Ranked by `impact_score = (loss_of_ALLOW − loss_of_REVIEW) / fixed_review_time`.

---

## Shadow mode

### POST /api/shadow-score
Scores a transaction through the candidate/shadow fraud model for drift comparison. **Requires `X-API-Key`.** Never affects the live decision — purely persisted for `GET /api/shadow-comparison`.
```json
{"transaction_id": "TXN-001", "fraud_probability": 0.42, "recommended_action": "ALLOW", "...features used by the shadow model...": 0}
```

### GET /api/shadow-comparison
**Requires `X-API-Key`.** Query: `limit` (default 100, max 1000). Returns recent primary-vs-shadow pairs plus aggregate drift stats (`primary_mean`, `shadow_mean`, `mean_abs_delta`, `flip_rate` — how often the shadow model would flip the 0.5 decision boundary vs. the primary).

---

## Metrics

### GET /api/metrics/model-performance
Serves `app/ml/artifacts/evaluation_metrics.json`, produced by running `python -m app.ml.evaluation`. If that file doesn't exist yet, returns `{"status": "not_ready", "message": "Run ml/evaluation.py to generate evaluation_metrics.json"}` instead of a 404 — check for this before quoting model numbers live.

### GET /api/metrics
Live aggregate dashboard numbers from the `decisions`/`overrides` tables (counts, action distribution, override rate, average savings) plus the model's precision/recall/F1 read from the same evaluation file when present.

---

## Insights

### GET /api/insights
Before/after learning-curve data for a dashboard chart. **On an empty database this returns hardcoded illustrative numbers, and even with real overrides the "after" values are a capped formula, not a recomputed model metric** — see `docs/ARCHITECTURE.md` §4.6 before presenting this as measured improvement.

---

## Audit

### GET /api/audit
Query: `limit` (default 50). No auth. Seeds demo rows if empty.

### GET /api/audit/decisions
Last 100 decisions in a compact audit-friendly shape. No auth.

---

## Configuration

There are two configuration endpoints. `/api/config` provides runtime in-memory configuration, while `/api/cost-config` provides persistent, auditable configuration backed by PostgreSQL.

### GET/PUT /api/config
In-memory runtime configuration. Changes reset when the process restarts. `GET` is public; `PUT` requires `X-API-Key`.

### GET/PUT /api/cost-config
PostgreSQL-backed and versioned through the `config_history` table. `GET` is public; `PUT` requires `X-API-Key`. Use this endpoint for persistent and auditable cost-model configuration.

---

## Learning / override loop

### GET /api/learning/override-stats
**Requires `X-API-Key`.** All-time and 7-day override rates, top override patterns, and whether retraining is recommended (>15% all-time or >10% in the last 7 days).

### GET /api/learning/override-feedback
**Requires `X-API-Key`.** Query: `limit` (default 50, max 500). Raw override + linked decision feature snapshots — the shape a retraining pipeline would actually consume.

### POST /api/learning/trigger-retrain
**Requires `X-API-Key`.** Reports whether retraining looks warranted and what it would involve. **Does not retrain anything** — see `docs/ARCHITECTURE.md` §4.6.

---

## Demo / dev-data helpers (`app/routes/demo.py`)

Used by the frontend's demo store to generate plausible-looking transactions without hammering the real models on every keystroke. Not part of the risk-decisioning contract — don't build integrations against these.

- `GET /api/demo/transaction` — one synthetic transaction, scored.
- `GET /api/demo/counterintuitive` — biased toward generating a counterintuitive case (high fraud prob, high LTV).
- `GET /api/demo/stream` — a batch of synthetic scored transactions.
- `POST /api/demo/seed-decisions` — writes synthetic `Decision` rows to the database for local/demo environments only. This endpoint should not be enabled for production use.

## Streaming

### GET /api/stream/transactions
Server-Sent Events. **Requires `X-API-Key`.** Query: `delay_ms` (100–10000, default 1800). Replays recent decisions as a live-looking ticker for the Command Center demo — it's driving synthetic pacing over real stored decisions, not a live production feed.

---

## Error codes

| Code | When |
|---|---|
| 400 | Bad payload, invalid action/config key, missing/invalid webhook signature |
| 401 | Missing or wrong `X-API-Key` |
| 404 | Transaction / webhook event not found |
| 409 | `transaction_id` already scored |
| 422 | Pydantic validation failure (e.g. `amount <= 0`) |
| 429 | Rate limit exceeded |
| 500 | Model inference failure, unconfigured `TIEBREAKER_API_KEY` in production |
| 503 | Razorpay credentials not configured |