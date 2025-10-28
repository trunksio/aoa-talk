# -----------------------------------------------------------------------------
# Parser Agent Dockerfile
# -----------------------------------------------------------------------------
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    python3 python3-pip git curl build-essential libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -----------------------------------------------------------------------------
# Copy shared packages
# -----------------------------------------------------------------------------
COPY shared/python /shared
RUN pip install --no-cache-dir -e /shared

# Copy common agent utilities (manifest + registration)
COPY agents/common /agents_common
RUN pip install --no-cache-dir -r /agents_common/requirements.txt

# -----------------------------------------------------------------------------
# Copy parser agent code and install dependencies
# -----------------------------------------------------------------------------
COPY agents/parser/ /app/
RUN pip install --no-cache-dir -r /app/requirements.txt || true

# -----------------------------------------------------------------------------
# Environment and registration config
# -----------------------------------------------------------------------------
ENV PYTHONPATH="/shared:/app:/agents_common:${PYTHONPATH}"
ENV MANIFEST_PATH="/app/manifest.yaml"
ENV REGISTRY_URL="http://registry:8001"

# -----------------------------------------------------------------------------
# Create startup script (AFTER code copy so it's not overwritten)
# -----------------------------------------------------------------------------
RUN echo '#!/bin/bash\n\
set -e\n\
echo "[INFO] Starting Parser Agent..."\n\
echo "[INFO] Registering agent with Registry service..."\n\
python3 /agents_common/register_on_start.py $MANIFEST_PATH || echo "[WARNING] Registration failed, continuing anyway"\n\
echo "[INFO] Starting agent worker..."\n\
exec python3 main.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# -----------------------------------------------------------------------------
# Healthcheck and startup
# -----------------------------------------------------------------------------
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://registry:8001/health || exit 1

CMD ["/app/start.sh"]
