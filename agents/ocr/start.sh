#!/bin/bash
set -e

echo "[INFO] Starting OCR Agent..."
echo "[INFO] Checking CUDA availability..."
python3 -c "import torch; print('[CHECK] CUDA available:', torch.cuda.is_available())"

# note: /app/agents_common because we copied it there in the Dockerfile
echo "[INFO] Registering agent with Registry service..."
python3 /app/agents_common/register_on_start.py "$MANIFEST_PATH" \
    || echo "[WARNING] Registration failed, continuing anyway"

echo "[INFO] Launching OCR worker..."
exec python3 /app/main.py
