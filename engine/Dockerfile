# GEO Audit Engine
# Builds from repo root so scripts/ is available at runtime.
#
# Build:
#   docker build -f engine/Dockerfile -t geo-engine .
#
# Run:
#   docker run -p 8000:8000 -e GEO_ENGINE_API_KEY=secret geo-engine

FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY engine/requirements.txt /app/engine/requirements.txt
RUN pip install --no-cache-dir -r /app/engine/requirements.txt

# Copy engine source and scripts (needed at runtime)
COPY engine/ /app/engine/
COPY scripts/ /app/scripts/

EXPOSE 8000

# Run from /app so that `from scripts.xxx import` works
CMD ["uvicorn", "engine.app:app", "--host", "0.0.0.0", "--port", "8000"]
