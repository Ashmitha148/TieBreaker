# TieBreaker

Cost-aware payment risk decisioning for **Razorpay Buildathon 2026, Track 2 (AI Risk Manager)**.

TieBreaker scores a transaction with two models (fraud and false-positive), then picks ALLOW / VERIFY / REVIEW / BLOCK by expected rupee loss — not by a single threshold. This README describes what is actually in this repository and what the evaluation script produced on a held-out test set. It does not invent business-impact percentages.

## Held-out metrics (from `ml/evaluation.py`, this run)

Leakage check: **PASS** — 4411 train IDs, 1769 test IDs, **0 overlap**.

Test set: 1769 records · fraud rate 18.9% · false-positive rate 7.3%.

| Model | Precision | Recall | F1 | PR-AUC | ROC-AUC | Brier |
|-------|-----------|--------|----|--------|---------|-------|
| Fraud Detector | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.0000 |
| False Positive | 0.594 | 0.146 | 0.235 | 0.344 | 0.841 | 0.0578 |

Fraud confusion matrix: `[[1435, 0], [0, 334]]`. FP confusion matrix: `[[1626, 13], [111, 19]]`.

The fraud model’s entire feature importance is `velocity_1h = 1.0` (every other fraud feature is 0.0). That, plus precision and recall both ≥ 0.97, is a **synthetic-data artifact**: labels in `backend/app/ml/data.py` are generated from the same velocity/geo/device rules the model then re-learns. Do not read 1.000 / 1.000 as production performance.

The false-positive model is the honest one on this set: 14.6% recall, Brier 0.0578. Per-merchant FP F1 on this run: B2B 0.558, Logistics 0.296, Retail 0.133, Services 0.125, Food 0.000, SaaS 0.000.

Full JSON (including per-merchant tables and the generated limitations write-up) is at `backend/app/ml/artifacts/evaluation_metrics.json`. Serve it via `GET /api/metrics/model-performance`.

## Implemented and demoable today

- Dual sklearn `GradientBoostingClassifier` artifacts (`fraud_model.pkl`, `fp_model.pkl`) plus a linear review-time model
- Held-out evaluation script: `ml/evaluation.py` (precision, recall, F1, PR-AUC, ROC-AUC, Brier, confusion matrix, per-merchant breakdown, feature importance, leakage check, dynamic honest assessment)
- `POST /api/transactions` — Pydantic body, required `customer_id`, Redis velocity with explicit `velocity_source` (`redis` or `fallback_zero`), idempotency on `transaction_id`, AuditLog write, model version from artifact metadata
- `POST /api/what-if` — independent probability overrides, sensitivity on the same fraud/FP probabilities as the decision
- `GET/POST /api/learning/*` — override stats with all-time **and** 7-day retrain triggers; `trigger-retrain` reports a recommendation and **does not train a new model**
- Razorpay webhook `POST /api/webhooks/razorpay` authenticated **only** by HMAC-SHA256 + `x-razorpay-event-id` idempotency (no API key)
- API key auth (`X-API-Key` / `TIEBREAKER_API_KEY`) on decisioning, what-if, and learning endpoints
- FastAPI + React (Vite) UI: checkout, command center, queue, learning stats, what-if panel
- Optional Redis velocity; if Redis is down the API still scores and says so
- Docker Compose for backend + Postgres + Redis (`docker-compose.yml`); backend `Dockerfile`

## Planned, not yet built

- JWT sessions (not implemented; API key is what exists)
- Automatic model retraining from overrides (the learning endpoint is a recommendation report)
- Production SHAP waterfall for every request (TreeExplainer is used when `shap` loads; otherwise heuristic drivers)
- Graph / device-fingerprint / multi-merchant federation features described in older architecture notes
- A live public demo URL — `https://tiebreaker-demo.vercel.app` returns 404 and is not linked here
- Claimed XGBoost models — training code uses sklearn gradient boosting, not XGBoost, even though `xgboost` is listed in requirements

## Architecture (what this repo actually deploys)

```
React (Vite)  --X-API-Key-->  FastAPI
                                  |
                    +-------------+-------------+
                    |             |             |
              POST /transactions  what-if    /learning/*
                    |             |             |
              VelocityEngine                 Postgres/SQLite
              (Redis or zeros)               Decisions, Overrides, AuditLog
                    |
              sklearn GBC fraud + FP
                    |
              Strike cost engine → ALLOW | VERIFY | REVIEW | BLOCK

Razorpay servers --HMAC--> POST /api/webhooks/razorpay
```

## Quick start

```bash
git clone https://github.com/Ashmitha148/TieBreaker.git
cd TieBreaker

# Backend (from repo root or backend/)
pip install -r backend/requirements.txt
# copy backend/.env.example → backend/.env and set TIEBREAKER_API_KEY
uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd frontend
cp .env.example .env   # VITE_API_KEY must match TIEBREAKER_API_KEY
npm install
npm run dev
```

Evaluate:

```bash
python ml/evaluation.py
```

Webhook URL to configure in Razorpay: `https://<your-backend>/api/webhooks/razorpay`.

## Authentication

| Surface | Auth |
|---------|------|
| `POST /api/transactions`, `POST /api/what-if`, `/api/learning/*` | `X-API-Key` matching `TIEBREAKER_API_KEY` |
| `POST /api/webhooks/razorpay` | HMAC-SHA256 (`X-Razorpay-Signature`) + event-id idempotency |
| Other GET demo routes | Unauthenticated in this build |

In `ENVIRONMENT=production`, a missing `TIEBREAKER_API_KEY` returns **500** (does not silently allow traffic). Wrong or missing header returns **401**.

Set the same value in Railway (`TIEBREAKER_API_KEY`) and Vercel (`VITE_API_KEY`).

## What broke during development and how it was fixed

**Silent what-if overrides.** If only one of `override_fraud_prob` / `override_fp_prob` was set, the code required both and fell through to full model inference with no warning. Overrides now apply independently; a partial override is labelled in the response. Sensitivity used hardcoded 0.5 / 0.2 instead of the transaction’s actual probabilities — it now uses the same pair as the decision.

**Leakage check that did not stop the run.** Train/test ID overlap was printed as FAIL and then metrics were still written. `ml/evaluation.py` now exits with status 1 and refuses to publish metrics if overlap exists or IDs cannot be read. Empty-string IDs are not treated as a fake overlap.

**Diluted retraining trigger.** Retrain used only the all-time override rate, so a week of drift could hide inside a long quiet history. Stats now also compute a 7-day rate (10% threshold) and recommend retraining on either signal.

**Auth in the wrong place.** Scoring endpoints had no shared-secret check; putting an API key on the Razorpay webhook would have broken delivery. Key auth is only on decisioning / what-if / learning. The webhook is unchanged.

**Redis failures looking like real zeros.** Bare `except Exception: pass` made a Redis bug indistinguishable from “customer has no recent txs.” Lookups now catch Redis/connection errors, log them, and return `velocity_source: fallback_zero`.

**Stale / empty project description.** The working-tree README was empty; the last committed README advertised a 404 demo URL, `yourusername` clone text, and invented monthly-loss tables. This file is the source of truth for GitHub visitors.

## Links that resolve

- Repository: https://github.com/Ashmitha148/TieBreaker
- Issues: https://github.com/Ashmitha148/TieBreaker/issues
- Docs in-repo: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API.md](docs/API.md), [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

Older docs still mention XGBoost, JWT, and 47 features. Prefer this README and the code when they disagree.

## License

MIT (see `LICENSE` if present in the repo).
