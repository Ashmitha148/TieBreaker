# TieBreaker

TieBreaker is a payment routing and strike decision engine.

## Phase 1: Real Razorpay Test Mode Payment Slice

Phase 1 provides a real Razorpay Test Mode payment vertical slice with asynchronous webhook processing and database persistence:
- **Demo Checkout:** React, TypeScript, Vite, Tailwind CSS with dynamic Razorpay Checkout.js modal integration.
- **Backend API:** FastAPI with server-side Razorpay order creation and client config endpoints.
- **Webhook Pipeline:** `POST /api/webhooks/razorpay` with raw-body HMAC-SHA256 verification, `x-razorpay-event-id` idempotency deduplication, fast HTTP 200 responses, and asynchronous database processing.
- **Persistence:** PostgreSQL-ready SQLAlchemy models (`Order`, `Payment`, `WebhookEvent`) with SQLite local fallback.
- **Deployment:** Prepared for Railway (Backend + PostgreSQL) and Vercel (Frontend) over HTTPS.

---

## Getting Started (Local Development)

### 1. Backend Setup
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # Linux/macOS
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Configure `.env` (copy from `.env.example`):
   ```env
   PROJECT_NAME="TieBreaker"
   ENVIRONMENT="development"
   DEBUG=true
   DATABASE_URL="sqlite:///./tiebreaker.db"
   RAZORPAY_KEY_ID="rzp_test_..."
   RAZORPAY_KEY_SECRET="..."
   RAZORPAY_WEBHOOK_SECRET="..."
   BACKEND_CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173"]
   ```
4. Run automated test suite:
   ```bash
   pytest
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

### 2. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   npm install
   ```
2. Run development server:
   ```bash
   npm run dev
   ```
3. Build for production:
   ```bash
   npm run build
   ```

---

## Production Deployment Guide

### A. Railway Backend & PostgreSQL
1. Create a project on [Railway](https://railway.app/).
2. Add a **PostgreSQL** database service.
3. Deploy the backend from GitHub repository:
   - **Root Directory:** `/backend`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Healthcheck Path:** `/health`
4. Set Environment Variables in Railway:
   - `RAZORPAY_KEY_ID`: `rzp_test_...`
   - `RAZORPAY_KEY_SECRET`: Your Razorpay Key Secret *(server-side only)*
   - `RAZORPAY_WEBHOOK_SECRET`: Your Razorpay Webhook Secret *(server-side only)*
   - `DATABASE_URL`: Automatically linked from Railway PostgreSQL
   - `BACKEND_CORS_ORIGINS`: `["https://<your-vercel-app>.vercel.app", "http://localhost:5173"]`
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `false`

### B. Vercel Frontend
1. Import repository to [Vercel](https://vercel.com/).
2. Configure project settings:
   - **Root Directory:** `frontend`
   - **Framework Preset:** `Vite`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Set Environment Variable in Vercel:
   - `VITE_API_URL`: `https://<your-railway-app>.up.railway.app`

### C. Razorpay Test Mode Webhook Configuration
In your [Razorpay Dashboard](https://dashboard.razorpay.com/) (*Test Mode*):
1. Go to **Account & Settings** → **Webhooks** → **+ Add New Webhook**.
2. **Webhook URL:** `https://<your-railway-app>.up.railway.app/api/webhooks/razorpay`
3. **Secret:** Set your `RAZORPAY_WEBHOOK_SECRET`.
4. **Active Events:**
   - `payment.authorized`
   - `payment.captured`
   - `payment.failed`
   - `order.paid`