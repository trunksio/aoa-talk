# Dockerfile for AOA Registry Service
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install shared package
COPY shared/python /shared
RUN pip install --no-cache-dir -e /shared

# Copy registry service code
COPY backend/registry/ /app/

# Install service requirements
RUN pip install --no-cache-dir -r requirements.txt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run migrations and start service
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8001
