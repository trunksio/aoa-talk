# -----------------------------------------------------------------------------
# DeepSeek-OCR GPU Agent for DGX Spark (GB10 GPU, CUDA 13.0, sm_121)
# -----------------------------------------------------------------------------
FROM nvidia/cuda:13.0.1-devel-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=${CUDA_HOME}/bin:${PATH} \
    LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# -----------------------------------------------------------------------------
# Python 3.12 and system dependencies
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    python3.12 python3.12-dev python3-pip \
    git git-lfs curl build-essential \
    libmagic1 poppler-utils libpoppler-dev libpoppler-cpp-dev \
    wget ca-certificates && \
    git lfs install && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Set working directory
# -----------------------------------------------------------------------------
WORKDIR /app

# -----------------------------------------------------------------------------
# Upgrade pip and install PyTorch 2.9.0 + CUDA 13.0 wheel
# -----------------------------------------------------------------------------
RUN python3 -m pip install --upgrade pip setuptools wheel \
    --ignore-installed --break-system-packages

# Attempt direct CUDA 13 wheel; fallback to cu124
RUN pip install --no-cache-dir --break-system-packages \
    torch==2.9.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130 || \
    pip install --no-cache-dir --break-system-packages \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# -----------------------------------------------------------------------------
# Core + dynamic dependencies for DeepSeek-OCR
# -----------------------------------------------------------------------------
RUN pip install --no-cache-dir --break-system-packages \
    transformers==4.39.3 sentencepiece accelerate addict einops easydict \
    numpy Pillow opencv-python-headless ninja packaging

# Build Flash-Attention from source (CUDA 13 compatible)
RUN pip install --no-cache-dir --break-system-packages "flash-attn==2.5.6" --no-build-isolation

# -----------------------------------------------------------------------------
# Cache DeepSeek-OCR repository snapshot (no dynamic import at build time)
# -----------------------------------------------------------------------------
RUN pip install --no-cache-dir --break-system-packages huggingface_hub

RUN python3 - <<'PYCODE'
from huggingface_hub import snapshot_download
print("Fetching DeepSeek-OCR model snapshot (revision 2c968b4)…")
snapshot_download(
    repo_id="deepseek-ai/deepseek-ocr",
    revision="2c968b4",
    local_dir="/root/.cache/huggingface/hub/models--deepseek-ai--deepseek-ocr",
    local_dir_use_symlinks=False,
    resume_download=True
)
print("DeepSeek-OCR model snapshot cached successfully.")
PYCODE

# -----------------------------------------------------------------------------
# Copy shared/common package and OCR agent code
# -----------------------------------------------------------------------------
COPY agents/common /app/agents_common
RUN pip install --no-cache-dir -r /app/agents_common/requirements.txt --break-system-packages

COPY agents/ocr/ /app/

# -----------------------------------------------------------------------------
# Copy the startup script (clean and version-controlled)
# -----------------------------------------------------------------------------
COPY agents/ocr/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# -----------------------------------------------------------------------------
# Set Python path - /app first for agent imports
# -----------------------------------------------------------------------------
ENV PYTHONPATH="/app:/app/agents_common:/shared:${PYTHONPATH}"

# -----------------------------------------------------------------------------
# Default command
# -----------------------------------------------------------------------------
CMD ["/app/start.sh"]
