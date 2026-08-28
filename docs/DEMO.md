# TieBreaker — App Walkthrough

A quick tour of all features. Useful for anyone exploring the app: judges, mentors, users, or teammates.

---

## 1. Landing Page

**URL**: http://localhost:5173

What you'll see:
- Particle network animation in the background (canvas-based, connects nearby dots)
- Dual-stream visualization — Legitimate (green) and Fraud (red) streams converging on an AI brain
- Animated counters that tick up when scrolled into view
- Gradient underline animation on "Payment Risk"
- Scroll-down chevron that bounces

What this shows:
The landing page tells the story visually: two transaction streams being intelligently separated by AI. It's not just a dashboard — it's a product narrative.

---

## 2. Checkout Demo

**URL**: http://localhost:5173/checkout
**Or**: Click "Try Live Demo" on the landing page

What to do:
1. Enter amount: 45000
2. Click "Pay Rs 45,000"
3. Watch the 6-step pipeline animation

What you'll see:
- Pipeline steps animate sequentially: Payment -> Velocity -> Fraud Model -> FP Model -> Decision -> Action
- Each step shows detail text (e.g., "prob: 0.72")
- Result card shows 4 metric boxes: Amount, Fraud Prob, FP Prob, Confidence
- Counterintuitive warning banner (if REVIEW is chosen over BLOCK)
- "New Payment" button resets the flow

What this shows:
Most fraud systems would BLOCK a 72% fraud case. TieBreaker says REVIEW because the cost model says so. The counterintuitive flag is the key differentiator.

---

## 3. Command Center

**URL**: http://localhost:5173/command
**Or**: Click "Command Center" in sidebar

What you'll see:
- Live ticker — scrolling transaction feed at top
- Transaction pipeline — 6 steps, initially idle
- 4 stat cards: Total Decisions, Fraud Prevented, Override Rate, Avg Review
- Live transactions table — 8 rows with risk bars, action pills, counterintuitive badges
- Model performance bars — gradient bars showing F1 scores

Try this:
Click any transaction row (e.g., pay_LxK9mN2pQr). The pipeline will populate with that transaction's data, then auto-navigate to the detail page after 600ms.

What this shows:
Real-time monitoring. Risk bars, action pills, and "Counter" badges give instant visual status.

---

## 4. Transaction Detail

**URL**: Auto-navigates from Command Center, or /transaction/pay_LxK9mN2pQr

What you'll see:
- Transaction pipeline — same 6 steps, now fully populated
- Decision timeline — timestamped journey with +ms durations
- Velocity flags — shows why the transaction was flagged
- SHAP explanation — feature importance bars (amount, velocity, device, etc.)
- What-If Simulator — two sliders + 4 action cost cards + recommendation
- Transaction details — Amount, probabilities, counterintuitive status
- Analyst override panel — 4 action buttons + reason textarea + submit

Try this:
1. Drag the Fraud Probability slider to 90% — watch the recommended action change
2. Drag the FP Probability slider to 40% — watch BLOCK become the cheapest option
3. Click an override action (e.g., ALLOW) — button highlights
4. Type a reason — textarea accepts input
5. Click "Submit Override" — toast notification appears

What this shows:
The analyst experience. Full explainability (SHAP), full traceability (timeline), full control (override), and full experimentation (What-If). No black boxes.

---

## 5. Queue Oracle

**URL**: http://localhost:5173/queue
**Or**: Click "Queue Oracle" in sidebar

What you'll see:
- Priority-ranked cards — highest impact score at top
- Impact score — composite metric (fraud + amount + LTV + wait time)
- Waiting time — shows how long each case has been queued
- Quick action buttons — ALLOW (green), BLOCK (red), REVIEW (amber), Details (arrow)

Try this:
Click the BLOCK button on any queue item. The card disappears with a smooth animation.

What this shows:
The system doesn't just detect — it orchestrates. Analysts get a prioritized todo list, not a random dump of alerts.

---

## 6. Override Learning

**URL**: http://localhost:5173/learning
**Or**: Click "Override Learning" in sidebar

What you'll see:
- Before/After toggle — click to switch between model versions
- 4 metric cards — Accuracy, Precision, Recall, F1 (percentages change)
- Learning curve chart — area chart showing accuracy improvement over 14 days
- Metrics improve when toggling to "After Overrides"

Try this:
Click the toggle button. Watch the 4 metric numbers animate from ~82% to ~91%.

What this shows:
The active learning loop. Every analyst override makes the next decision better.

---

## 7. Performance Dashboard

**URL**: http://localhost:5173/performance
**Or**: Click "Performance" in sidebar

What you'll see:
- 3 financial impact cards — Fraud Prevented, FP Revenue Saved, Total Savings
- Fraud vs FP trend chart — dual area chart over 14 days
- Decision distribution donut — ALLOW, VERIFY, REVIEW, BLOCK breakdown
- Color-coded legend

What this shows:
ROI in rupees. Not accuracy percentages — actual money saved.

---

## 8. System Configuration

**URL**: http://localhost:5173/config
**Or**: Click "System Config" in sidebar

What you'll see:
- 5 slider controls — Fraud Threshold, FP Threshold, Review Cost, Fraud Multiplier, LTV Weight
- Real-time value display — number updates as you drag
- Save button — gradient button with hover glow
- Reset button — reverts to defaults

Try this:
Drag the Fraud Threshold slider from 0.72 to 0.85. Click Save. Toast confirms.

What this shows:
Different merchants have different risk appetites. TieBreaker is configurable, not one-size-fits-all.

---

## 9. Audit Trail

**URL**: http://localhost:5173/audit
**Or**: Click "Audit Trail" in sidebar

What you'll see:
- Filterable table — filter by transaction ID or action
- Colored action badges — green ALLOW, red BLOCK, amber REVIEW, cyan VERIFY
- Analyst attribution — shows who made each override
- Model version tracking — every decision tagged with v2.0.0
- Reason field — shows WHY overrides happened

Try this:
Type "REVIEW" in the filter box. Only REVIEW actions remain.

What this shows:
SOC 2 readiness. Regulators and auditors need this. Razorpay needs this.

---

## 10. Status Bar

Visible on every dashboard page (bottom of screen)

What you'll see:
- API latency — updates every second (random 5-25ms)
- Model version — shows v2.0.0
- Live clock — IST timezone

What this shows:
Small detail, big impact. Makes the dashboard feel like real infrastructure, not a mockup.

---

## Known Limitations

1. Models are mocked — we use realistic probability distributions, not trained XGBoost models (would need 6+ months of labeled transaction data)
2. No real Razorpay integration in demo — the /api/create-order endpoint falls back to mock data when Razorpay credentials aren't configured
3. Single-tenant — multi-merchant federation is designed but not implemented

BUT: The architecture, API contracts, and UI are production-ready. Drop in real models + Razorpay keys and it works.

---

## Documentation

| File | Purpose |
|------|---------|
| README.md | Project overview, quick start, business impact |
| ARCHITECTURE.md | Deep system design, data flow, DB schema, cost model |
| API.md | Full REST API documentation with examples |
| PITCH.md | Presentation script with Q&A prep |
| DEMO.md | This file — feature walkthrough |

---

Razorpay Buildathon 2026 — TieBreaker Team
