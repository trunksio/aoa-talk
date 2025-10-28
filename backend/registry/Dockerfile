# Dockerfile for AOA Registry Service
FROM python:3.11-slim

# ---- system dependencies -----------------------------------------------------
RUN apt-get update && apt-get install -y \
    curl git build-essential postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- copy code ---------------------------------------------------------------
# Shared Python utilities
COPY shared/python /app/shared

# Entire backend folder so backend.registry imports work
COPY backend /app/backend

# ---- install dependencies ----------------------------------------------------
# Install shared package
RUN pip install --no-cache-dir -e /app/shared

# Install registry-specific requirements
RUN pip install --no-cache-dir -r /app/backend/registry/requirements.txt

WORKDIR /app/backend/registry
# ---- environment -------------------------------------------------------------
ENV PYTHONPATH="/app:${PYTHONPATH}"

# ---- healthcheck -------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# ---- run migrations & start FastAPI -----------------------------------------
CMD alembic -c /app/backend/registry/alembic.ini upgrade head && \
    uvicorn backend.registry.main:app --host 0.0.0.0 --port 8001
