# Dockerfile for CAVIA OCR Agent with DeepSeek-OCR
# Optimized for NVIDIA DGX Spark (GB10 GPU, ARM64, CUDA 13.0, sm_121)

FROM nvcr.io/nvidia/cuda:13.0.1-devel-ubuntu24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3-pip \
    curl \
    git \
    git-lfs \
    build-essential \
    libmagic1 \
    poppler-utils \
    libpoppler-dev \
    libpoppler-cpp-dev \
    wget \
    ca-certificates \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# Set python3.12 as default python
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

WORKDIR /app

# Upgrade pip (use --break-system-packages for Ubuntu 24.04 PEP 668 compliance)
# Use --ignore-installed to avoid conflicts with Debian packages
RUN python3 -m pip install --upgrade pip setuptools --break-system-packages --ignore-installed

# Install PyTorch 2.9.0 with CUDA 13.0 support for ARM64
# These wheels support the GB10 GPU (sm_121 compute capability)
# Note: PyTorch 2.9.0 may not be available yet, will try 2.5.1 with CUDA 12.4
RUN pip3 install --no-cache-dir --break-system-packages \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124 || \
    pip3 install --no-cache-dir --break-system-packages torch torchvision torchaudio

# Copy and install shared package first (for cavia_common)
COPY shared/python /shared
RUN pip install --no-cache-dir --break-system-packages -e /shared

# Copy OCR agent code
COPY agents/ocr/ /app/

# Copy parser agent's LLM extractor (for reuse)
COPY agents/parser/parsers/ /app/../parser/parsers/

# Install OCR agent requirements
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Pre-download DeepSeek-OCR model to reduce startup time
# This will cache the model in the container (optional, can fail without breaking build)
RUN python3 -c "from transformers import AutoModel, AutoProcessor; \
    print('Downloading DeepSeek-OCR model...'); \
    AutoProcessor.from_pretrained('deepseek-ai/deepseek-ocr', trust_remote_code=True); \
    AutoModel.from_pretrained('deepseek-ai/deepseek-ocr', trust_remote_code=True); \
    print('Model downloaded successfully')" || echo "Model download will happen at runtime (this is OK)"

# Set Python path
ENV PYTHONPATH="/shared:/app:/app/../parser:${PYTHONPATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import torch; import sys; sys.exit(0 if torch.cuda.is_available() else 1)"

# Run agent
CMD ["python", "main.py"]
