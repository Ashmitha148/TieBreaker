# TieBreaker Deployment Guide

Razorpay Buildathon 2026

---

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ and npm
- Python 3.11+ (for local backend dev)
- Razorpay API Keys (for live payment integration)

---

## Quick Start — Docker (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/Ashmitha148/TieBreaker.git
cd tiebreaker

# 2. Set environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your Razorpay keys

# 3. Start everything
docker-compose up --build

# 4. Open http://localhost:5173
```

---

## Manual Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

---

## Environment Variables

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/tiebreaker

# Redis
REDIS_URL=redis://localhost:6379

# Razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx

# JWT
JWT_SECRET=your-super-secret-key
JWT_EXPIRY_MINUTES=15

# Model paths
FRAUD_MODEL_PATH=models/fraud_xgb_v2.pkl
FP_MODEL_PATH=models/fp_xgb_v2.pkl
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
```

---

## Production Build

```bash
# Frontend
cd frontend
npm run build
# Output: dist/ folder

# Backend
cd backend
docker build -t tiebreaker-backend .
```

---

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/tiebreaker
      - REDIS_URL=redis://redis:6379
      - RAZORPAY_KEY_ID=${RAZORPAY_KEY_ID}
      - RAZORPAY_KEY_SECRET=${RAZORPAY_KEY_SECRET}
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=tiebreaker
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## Vercel Deployment (Frontend)

```bash
cd frontend

# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

---

## Railway/Render Deployment (Backend)

1. Push code to GitHub
2. Connect Railway/Render to repo
3. Set environment variables in dashboard
4. Deploy

---

## Troubleshooting

### Port already in use

```bash
# Kill process on port 5173
npx kill-port 5173

# Or change port
npm run dev -- --port 3000
```

### CORS errors

Ensure backend has CORS configured:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Build fails

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Type check
npx tsc --noEmit
```

---

Razorpay Buildathon 2026
