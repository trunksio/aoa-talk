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

# Copy and install agents/common package (for manifest and registration)
COPY agents/common /agents_common
RUN pip install --no-cache-dir -r /agents_common/requirements.txt

# Copy parser agent code
COPY agents/parser/ /app/

# Install parser requirements
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model using pip
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl

# Set Python path
ENV PYTHONPATH="/shared:/app:/agents_common:${PYTHONPATH}"

# Set environment variables for registration
ENV MANIFEST_PATH="/app/manifest.yaml"
ENV REGISTRY_URL="http://registry:8000"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Create startup script that registers agent then starts main process
RUN echo '#!/bin/bash\n\
set -e\n\
echo "[INFO] Starting Parser Agent..."\n\
echo "[INFO] Registering agent with Registry service..."\n\
python3 /agents_common/register_on_start.py $MANIFEST_PATH || echo "[WARNING] Registration failed, continuing anyway"\n\
echo "[INFO] Starting agent worker..."\n\
exec python3 main.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run agent with registration
CMD ["/app/start.sh"]
