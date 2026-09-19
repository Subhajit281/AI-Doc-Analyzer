# Multi-stage lightweight Dockerfile optimized for <= 512 MB Free-Tier Platforms
# (Render, Railway, Fly.io, Hugging Face Spaces)

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools only for compiling any wheels if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-free-tier.txt .
RUN pip install --no-cache-dir --user -r requirements-free-tier.txt

# Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Critical memory optimization environment variables:
# - MALLOC_ARENA_MAX=2 prevents glibc memory fragmentation in multi-threaded Python
# - PARSER_BACKEND=lightweight ensures zero-vision, low-memory document parsing
# - EMBEDDING_PROVIDER=gemini offloads embedding computation to Google API (0 MB local RAM)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2 \
    PARSER_BACKEND=lightweight \
    EMBEDDING_PROVIDER=gemini \
    PORT=8000

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy backend code
COPY . .

# Create data directories
RUN mkdir -p data/documents chroma_db

EXPOSE 8000

# Single worker is mandatory for 512 MB memory allowance; dynamically honors cloud-assigned $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 30"]

