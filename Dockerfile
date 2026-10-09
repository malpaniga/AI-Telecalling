# AI Telecalling SaaS — API/Web Dockerfile
# Target: Fly.io (amd64 Linux)
# Python 3.13, uvicorn with uvloop

FROM python:3.13-slim AS base

# Security: run as non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ backend/
COPY .env.example .env.example

# Create models directory (populated via Fly Volume)
RUN mkdir -p /app/models/silero /app/models/piper

# Non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Graceful shutdown: uvicorn catches SIGTERM
CMD ["python", "-m", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "2", \
     "--loop", "auto", \
     "--timeout-graceful-shutdown", "30", \
     "--access-log"]
