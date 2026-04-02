FROM python:3.12-slim AS base

# No .pyc files, unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (pdf2image needs poppler for DOCX→PDF pipeline)
RUN apt-get update && \
    apt-get install -y --no-install-recommends poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY pyproject.toml ./
RUN pip install --no-cache-dir . 2>/dev/null || true

# Copy source
COPY src/ src/
COPY data/ data/

# Install PyTorch CPU-only first (much smaller than full CUDA build)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install the project with optional dependencies
RUN pip install --no-cache-dir ".[annotation,additives,designer,catalog,docx-convert,ocr,saliency]"

# Dirs for runtime
RUN mkdir -p logs data

# Streamlit config
COPY .streamlit/ .streamlit/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

ENTRYPOINT ["streamlit", "run", "src/fediaf_verifier/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--browser.gatherUsageStats=false"]
