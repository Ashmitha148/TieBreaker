# TieBreaker — Demo Script

A walkthrough for anyone evaluating the live app: judges, mentors, or the team rehearsing before judging. Written against the routes actually wired into `App.tsx` today.

**Before presenting, check `GET /health`.** If `ml.fraud_model_loaded` or `ml.fp_model_loaded` is `false`, the affected model-backed functionality may use the heuristic fallback instead of the trained XGBoost model.

---

## The one thing to get right: which flow you demo

TieBreaker's actual differentiator — expected-loss optimization producing a "counterintuitive" REVIEW over a naive BLOCK — lives in the **Strike Decision Engine**, which is only exercised by `POST /api/transactions` and `POST /api/what-if`. The `/checkout` page (real Razorpay integration) currently runs a **simpler fixed-threshold** decision, not the Strike Engine (`docs/ARCHITECTURE.md` §2).

**So: demo the Razorpay integration to prove the payments plumbing is real, and demo the What-If Simulator or Command Center to prove the cost-optimization story.** Don't rely on `/checkout` alone to show off the engine — it won't produce the counterintuitive result you want to talk about.

---

## 1. Landing (`/`)

Particle-field canvas animation, animated stat counters, product framing. Nothing to interact with — a 10-second establishing shot, not a feature.

## 2. Checkout (`/checkout`)

**What it proves**: real Razorpay Test Mode integration — a real Razorpay Test Mode order is created via the Razorpay Orders API, Checkout.js opens, and the returned signature is verified server-side (`docs/API.md` — Orders/Payments).

**What it doesn't prove**: the cost-optimizing decision (see above — this path uses a fixed fraud-probability threshold).

Enter an amount, complete the Razorpay Test Mode checkout (use Razorpay's published test card/UPI credentials, not real payment details), and point out the signature verification step in `POST /api/payment/verify` if asked how integrity is enforced.

## 3. Command Center (`/command`)

Pulls `GET /api/metrics` and `GET /api/queue`. Click a transaction row to navigate to its detail page.

## 4. What-If Simulator — the actual centerpiece

Reachable from the Transaction Detail page, or directly via `POST /api/what-if`. This is where to make the "counterintuitive" case land:

1. Set a high fraud probability (or amount) and a high LTV.
2. Show the four losses side-by-side (`financial_analysis.losses_by_action`) and point out that REVIEW (or VERIFY) beats BLOCK once LTV is in the picture.
3. Nudge LTV down 20% via `parameter_sensitivity` and show how the recommendation changes, if the selected scenario crosses the decision boundary — this demonstrates the decision is genuinely sensitive to the economics, not just cosmetic.

If the transaction-detail page's fetch bug (above) isn't fixed yet, this is also the safest way to demo the engine directly — If the transaction-detail page is unavailable, use the What-If Simulator directly as the fallback demonstration path.

## 5. Queue (`/queue`)

`GET /api/queue`, ranked by impact score. Falls back to clearly-labeled synthetic demo cases (`"source": "demo"`) if the database is empty — If the database is empty, run `POST /api/demo/seed-decisions` before the demo so the queue is populated with clearly identified demo data.

## 6. Override Learning (`/learning`)

Shows a before/after metrics toggle backed by `GET /api/insights`. **Say this out loud if asked**: on a fresh database these numbers are illustrative placeholders, not a measured accuracy improvement (`docs/ARCHITECTURE.md` §4.6). The override *logging* and *rate-threshold recommendation* (`GET /api/learning/override-stats`) are real; the learning-curve chart's specific numbers are not.

## 7. Performance (`/performance`)

Financial-impact cards and trend charts from `GET /api/metrics`. Good for the "ROI in rupees, not accuracy points" framing.

## 8. Shadow Mode (`/shadow`)

Not in the original demo script but fully implemented: shows the candidate model scored alongside the primary model, with drift stats (`GET /api/shadow-comparison`). Good talking point for MLOps maturity if a judge asks "how would you roll out a new model safely?" — the honest answer is "this shadow-mode pipeline exists and works, but there's no automatic promotion yet."

## 9. Config (`/config`)

Cost-parameter tuning. Mention there are two backing endpoints (`/api/config`, in-memory; `/api/cost-config`, persisted) if asked about config durability — see `docs/API.md`.

## 10. Audit (`/audit`)

Filterable decision/override log. Good for demonstrating auditability and decision traceability — append-only by convention (no delete route exists on `AuditLog`).

---

## Pre-demo checklist

- [ ] `GET /health` → `ml.fraud_model_loaded: true`, `ml.fp_model_loaded: true`
- [ ] `POST /api/demo/seed-decisions` run once so Queue/Command Center have data
- [ ] Razorpay Test Mode credentials configured and `POST /api/payment/create-order` successfully creates a test order
- [ ] Know the transaction-detail route bug (§3) and have the What-If path ready as the fallback
- [ ] Decide in advance whether you're demoing `/checkout` (payments plumbing) or What-If/Command Center (cost engine) for the "counterintuitive" story — don't conflate them live