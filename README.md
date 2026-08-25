# TieBreaker

TieBreaker is a payment routing and strike decision engine.

## Phase 0 Foundation

This repository contains the clean foundation setup for the TieBreaker project:
- **Backend:** FastAPI, SQLAlchemy, Pydantic Settings, PostgreSQL-ready configuration with SQLite local fallback.
- **Frontend:** React, TypeScript, Vite, Tailwind CSS.
- **Project Structure:** `backend/`, `frontend/`, `tests/`, `ml/`, `data/`, `docs/`.

## Getting Started

### Backend Setup
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Run tests:
   ```bash
   pytest
   ```
4. Run development server:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run development server:
   ```bash
   npm run dev
   ```
4. Build for production:
   ```bash
   npm run build
   ```
