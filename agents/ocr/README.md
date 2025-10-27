# DeepSeek-OCR Agent

An agentic unit for extracting structured data from scanned and image-based CVs using DeepSeek-OCR, a state-of-the-art OCR model optimized for document processing.

## Overview

This agent is part of the CAVIA Agent-Oriented Architecture (AOA) and specializes in processing CVs that are:
- Scanned documents (image-based PDFs)
- JPG/PNG images of resumes
- Documents with charts, graphs, and complex layouts
- Poor quality or low-resolution scans

## Features

- **Advanced OCR**: Uses DeepSeek-OCR model for high-accuracy text extraction
- **GPU Accelerated**: Optimized for NVIDIA DGX Spark (GB10 GPU with sm_121 compute capability)
- **Multi-format Support**: PDF, PNG, JPG, JPEG, TIFF
- **Structured Extraction**: Combines OCR with LLM-based parsing for structured data
- **Semantic Discovery**: Self-registers and integrates via intent-based routing
- **Production Ready**: Full error handling, logging, and monitoring

## Architecture

```
OCRAgent (BaseAgent)
├── DeepSeekOCRProcessor
│   ├── Model: deepseek-ai/deepseek-ocr (6.6GB)
│   ├── Backend: PyTorch 2.9.0 + CUDA 13.0
│   └── Modes: free_ocr, markdown, grounding
├── LLMCVExtractor (reused from parser)
│   └── Ollama for structured data extraction
└── Integration
    ├── MinIO: File storage
    ├── PostgreSQL: Metadata storage
    └── Redis RQ: Task queue (cv-ocr)
```

## Agent Capabilities

**Agent Type**: `ocr`

**Queue Name**: `cv-ocr`

**Task Type**: `extract_from_image_cv`

**Description**: Extracts structured data from scanned image-based CVs, documents with charts and graphs using advanced OCR technology

**Supported Formats**:
- PDF (scanned)
- PNG, JPG, JPEG
- TIFF, BMP

**Extraction Features**:
- Scanned documents
- Image-based CVs
- Charts and graphs
- Complex layouts
- Contact information
- Education history
- Work experience
- Skills
- Certifications

## Usage

### Intent-Based Routing

The OCR agent is automatically selected when users provide intents like:

```
"Extract structured data from scanned CV with charts"
"Process image-based resume"
"OCR this scanned document and extract CV data"
```

### Task Payload

```json
{
  "task_id": "uuid",
  "task_type": "extract_from_image_cv",
  "payload": {
    "job_id": "uuid",
    "filename": "scanned_cv.pdf",
    "minio_bucket": "cvs-raw",
    "minio_path": "uploads/job-123/scanned_cv.pdf"
  },
  "intent": "Extract from scanned CV",
  "steps_completed": []
}
```

### Output

The OCR agent outputs a `ParsedCV` object with:

```python
ParsedCV(
    contact_info={
        "name": "...",
        "email": "...",
        "phone": "...",
        "location": "...",
        "linkedin": "...",
        "github": "..."
    },
    education=[...],
    experience=[...],
    skills=[...],
    certifications=[...],
    raw_text="...",  # OCR-extracted text
    metadata={
        "filename": "...",
        "ocr_metadata": {...},
        "parser_version": "1.0.0-deepseek-ocr",
        "extraction_method": "deepseek_ocr_plus_llm"
    }
)
```

## Hardware Requirements

### Recommended
- NVIDIA DGX Spark (GB10 GPU)
- CUDA 13.0+
- 16GB+ GPU RAM
- ARM64 or x86_64 CPU

### Minimum
- Any NVIDIA GPU with compute capability sm_121+
- 8GB+ GPU RAM
- CUDA 13.0+

### CPU Fallback
- Works on CPU but significantly slower
- Not recommended for production

## Performance

Based on DeepSeek-OCR benchmarks:
- **Speed**: 24-58 seconds per page (depending on mode)
- **Throughput**: 200,000+ pages/day on single A100 GPU
- **Accuracy**: 97% on average documents
- **Compression**: Up to 10x token reduction vs raw text

## Installation & Deployment

### Docker Build

```bash
# Build the OCR agent image
docker build -t cavia-ocr:latest -f agents/ocr/Dockerfile .
```

### Docker Compose

The agent is already configured in `docker-compose.yml`:

```bash
# Start all services including OCR agent
docker compose up -d

# Start only OCR agent
docker compose up -d ocr-agent

# View OCR agent logs
docker compose logs -f ocr-agent

# Check GPU availability
docker exec cavia-ocr-agent python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
```

### Environment Variables

```bash
# Agent Configuration
AGENT_ID=ocr-001

# Infrastructure
DATABASE_URL=postgresql://cavia:password@postgres:5432/cavia
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false

# Ollama LLM
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2

# GPU Settings
CUDA_VISIBLE_DEVICES=0
TOKENIZERS_PARALLELISM=false

# Logging
LOG_LEVEL=INFO
```

## Development

### Local Testing

```bash
# Run tests
cd agents/ocr
pytest tests/ -v

# Test OCR processor directly
python -c "from ocr_processor import DeepSeekOCRProcessor; p = DeepSeekOCRProcessor(); print(p.get_model_info())"
```

### Debugging

```bash
# Access container
docker exec -it cavia-ocr-agent bash

# Check model loading
python -c "from transformers import AutoModel; AutoModel.from_pretrained('deepseek-ai/deepseek-ocr', trust_remote_code=True)"

# Test CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"
```

## Integration Flow

1. **User uploads scanned CV** with intent "Extract from scanned CV"
2. **Backend API** uses semantic discovery to find OCR agent
3. **Task enqueued** to `cv-ocr` queue
4. **OCR Agent processes**:
   - Downloads file from MinIO
   - Runs DeepSeek-OCR extraction
   - Uses LLM for structured parsing
   - Stores ParsedCV in database and MinIO
5. **Discovers EvaluatorAgent** and enqueues next task
6. **Evaluation continues** through standard agent chain

## Monitoring

### Health Checks

```bash
# Container health (GPU check)
docker inspect cavia-ocr-agent | grep Health

# RQ Dashboard
# http://localhost:9181 - Monitor cv-ocr queue
```

### Logs

```bash
# Follow agent logs
docker compose logs -f ocr-agent

# Check for errors
docker compose logs ocr-agent | grep ERROR
```

## Troubleshooting

### Model Download Issues

If the model doesn't download during build:

```bash
# Download manually in container
docker exec cavia-ocr-agent python -c "from transformers import AutoModel, AutoProcessor; AutoProcessor.from_pretrained('deepseek-ai/deepseek-ocr', trust_remote_code=True); AutoModel.from_pretrained('deepseek-ai/deepseek-ocr', trust_remote_code=True)"
```

### CUDA Compatibility

If you get CUDA errors:

```bash
# Check GPU compute capability
nvidia-smi --query-gpu=compute_cap --format=csv

# Ensure PyTorch version matches
docker exec cavia-ocr-agent python -c "import torch; print(torch.__version__, torch.version.cuda)"
```

### Memory Issues

If GPU runs out of memory:

```python
# Reduce batch size or use CPU for specific documents
# In ocr_processor.py, you can force CPU:
processor = DeepSeekOCRProcessor(device="cpu")
```

## References

- [DeepSeek-OCR Model](https://huggingface.co/deepseek-ai/deepseek-ocr)
- [Simon Willison's DGX Spark Implementation](https://simonwillison.net/2025/Oct/20/deepseek-ocr-claude-code/)
- [NVIDIA DGX Spark Documentation](https://lmsys.org/blog/2025-10-13-nvidia-dgx-spark/)
- [PyTorch CUDA Wheels](https://download.pytorch.org/whl/torch/)

## License

Part of the CAVIA project. See project root for license information.
