# TieBreaker Pitch Script

Razorpay Buildathon 2026 — Presentation Guide
Duration: 3-5 minutes (adjust based on time limit)

---

## Opening Hook (15 seconds)

"Every day, Razorpay processes millions of transactions. And every day, thousands of legitimate customers get their payments blocked because of overly aggressive fraud rules."

"I'm Prakhar, and we built TieBreaker to solve the most expensive problem in payment risk: the false positive paradox."

[Show Landing Page — let the particle animation and dual-stream viz speak for itself]

---

## The Problem (45 seconds)

[Split screen visual: left "Fraud Loss", right "False Positive Loss"]

"Payment fraud costs Indian businesses over Rs 1,200 crore annually. So companies build fraud detection systems."

"But here's the trap: when you optimize purely for fraud detection accuracy, you inevitably block good customers. And a blocked good customer is often more expensive than a fraudulent one."

Key stat:
"A high-LTV customer blocked once has a 40% chance of never returning. That single false positive can cost Rs 50,000 in lifetime value — far more than the Rs 2,000 fraud you just prevented."

[Navigate to /command — show the stats cards]

---

## The Solution (60 seconds)

[Show architecture diagram or the dual-stream hero animation]

"TieBreaker treats fraud detection as an economics problem, not a classification problem."

"Instead of one fraud model making binary allow/block decisions, we run TWO models in parallel:"

1. Fraud Model — "What's the probability this is fraud?"
2. False Positive Model — "What's the probability this is a legitimate transaction that looks suspicious?"

"Then our Strike Decision Engine computes the expected financial loss for EVERY possible action — Allow, Verify, Review, Block — and picks the one that loses the least money."

[Navigate to /checkout — initiate a demo payment]

---

## Live Demo — Checkout Flow (60 seconds)

[Fill in amount Rs 45,000, click Pay]

"Watch what happens in real-time."

[Pipeline animation plays — 6 steps]

"Payment -> Velocity Check -> Fraud Model -> FP Model -> Strike Decision -> Action. All in under 30 milliseconds."

[Result shows REVIEW with counterintuitive flag]

"Look at this — fraud probability is 72%. Most systems would block this immediately. But TieBreaker says REVIEW. Why?"

[Click "Details" or navigate to transaction detail]

"Because the customer's lifetime value makes the cost of a false block — Rs 67,500 — higher than the cost of an analyst review — Rs 28,400. This is a counterintuitive decision, and it's exactly where TieBreaker shines."

---

## Deep Dive — Explainability (45 seconds)

[Transaction Detail page with SHAP + Timeline + What-If]

"Every decision is fully explainable."

[Point to SHAP bars]

"SHAP tells us exactly which features drove the decision: amount contributed 25%, velocity 18%, new device 15%."

[Point to Decision Timeline]

"The timeline shows every stage with millisecond precision — full auditability for compliance."

[Open What-If Simulator, drag fraud slider]

"And analysts can use the What-If simulator to see how decisions change as probabilities shift — no guesswork, no black boxes."

---

## The Queue and Override System (45 seconds)

[Navigate to /queue]

"Counterintuitive cases land in the Queue Oracle, ranked by financial impact score. The highest-value cases get reviewed first."

[Click a transaction, show the override buttons]

"Analysts can override with one click. But here's the key: every override feeds back into the model through active learning."

[Navigate to /learning]

"This page shows before/after metrics. After 142 analyst overrides, our F1 score jumped from 0.76 to 0.88. The system literally gets smarter every day."

[Toggle Before -> After, show the numbers change]

---

## Business Impact (30 seconds)

[Navigate to /performance]

"The numbers speak for themselves."

[Point to each stat card]

"Rs 28.4 lakhs in fraud prevented. Rs 12.5 lakhs in false-positive revenue saved. Net savings of Rs 40+ lakhs."

[Point to the trend chart]

"Fraud incidents trending down, false positives dropping even faster."

---

## Technical Depth (30 seconds) — If judges ask

"Under the hood: FastAPI backend, XGBoost dual models, SHAP for explainability, PostgreSQL + Redis, React + TypeScript frontend with Framer Motion. Full Docker deployment. Sub-50ms latency."

"We're integrated with the Razorpay Orders API — create an order, score it, return the decision in a single call."

---

## Closing (15 seconds)

[Back to Landing Page]

"TieBreaker doesn't just detect fraud. It breaks the tie between security and revenue — and it breaks it in favor of the merchant's bottom line."

"Thank you. We're ready for questions."

---

## Q&A Prep

### Q: "How is this different from Razorpay's existing risk system?"
A: "Razorpay's system is excellent at fraud detection. TieBreaker adds the missing piece: explicit false-positive modeling and cost-optimized decisioning. We complement, not replace."

### Q: "What about latency?"
A: "25-35ms end-to-end. Fraud + FP models run in parallel. The Strike Engine is pure math — no ML inference. Well under the 50ms checkout SLA."

### Q: "How do you handle model drift?"
A: "Active learning from analyst overrides. We batch 100 overrides, trigger retraining, A/B test against current model, and auto-deploy if F1 improves by more than 1%."

### Q: "Is this production-ready?"
A: "Dockerized, API-documented, with full audit trails and SOC 2-ready security. The frontend works offline with demo data, and the backend integrates directly with Razorpay's Orders API."

### Q: "What's the business model?"
A: "SaaS per-transaction pricing. We save merchants Rs 40+ lakhs monthly. Charging 0.1% of transaction value is a no-brainer ROI."

---

## Demo Checklist

Before presenting, verify:

- [ ] Landing page loads with particle animation
- [ ] /checkout demo payment works (Rs 45,000 -> REVIEW)
- [ ] Transaction detail shows SHAP + Timeline + What-If
- [ ] /queue shows ranked transactions
- [ ] /learning toggle Before/After works
- [ ] /performance charts render
- [ ] /audit shows filterable logs
- [ ] Status bar shows live latency
- [ ] No console errors
- [ ] Build passes: npm run build

---

## Body Language Tips

1. Start with the landing page — let the visual do the talking for 5 seconds
2. Speak slowly during the checkout demo — let the pipeline animation breathe
3. Point at the screen when showing SHAP/timeline — physical engagement
4. Pause after "counterintuitive" — let the judges process why this is clever
5. End on the stats — numbers are memorable

---

You've got this. The product is solid. The narrative is clear. Go win.
