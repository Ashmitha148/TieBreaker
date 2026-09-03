FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p app/ml/artifacts

# Build-time guard: production requires the ML artifacts to be baked into the image.
RUN test -f app/ml/artifacts/fraud_model.joblib \
    && test -f app/ml/artifacts/fp_model.joblib \
    || (echo "ERROR: required ML artifacts missing from app/ml/artifacts/" && exit 1)

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]