# Dockerfile for CAVIA Reporter Agent

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install shared package
COPY shared/python /shared
RUN pip install --no-cache-dir -e /shared

# Copy common agent utilities (manifest + registration)
COPY agents/common /agents_common
RUN pip install --no-cache-dir -r /agents_common/requirements.txt

# Copy reporter agent code
COPY agents/reporter/ /app/

# Install reporter requirements
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path - /app first for agent imports
ENV PYTHONPATH="/app:/agents_common:/shared:${PYTHONPATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run agent
CMD ["python", "main.py"]
