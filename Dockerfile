# Base image
FROM python:3.11-slim

# Prevent python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app

# System deps (curl useful for health checks/debug), and clean up apt cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Copy manifests first to leverage Docker layer caching
COPY requirements.txt pyproject.toml README.md ./

# Install Python deps, then install the package so ADK can discover apps via [tool.adk]
RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && pip install .

# Copy source
COPY root_agent/ ./root_agent/
COPY docs/ ./docs/

# Container runtime configuration
ENV PORT=8080
EXPOSE 8080

# Security: run as non-root
USER appuser

# Launch ADK web server (UI + API) on Cloud Run's default port
CMD ["adk", "web", "--host=0.0.0.0", "--port=8080"]
