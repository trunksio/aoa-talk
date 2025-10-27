# Dockerfile for CAVIA Parser Agent

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install shared package
COPY shared/python /shared
RUN pip install --no-cache-dir -e /shared

# Copy parser agent code
COPY agents/parser/ /app/

# Install parser requirements
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model using pip
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl

# Set Python path
ENV PYTHONPATH="/shared:/app:${PYTHONPATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run agent
CMD ["python", "main.py"]
