# =============================================================================
# SDTM Pipeline - LangGraph Application
# Multi-stage build for optimized production image
# =============================================================================

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (using docker-specific requirements without Airflow)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-docker.txt

# =============================================================================
# Production stage
# =============================================================================
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY sdtm_pipeline/ ./sdtm_pipeline/
COPY etl_neo4j/ ./etl_neo4j/
COPY langgraph.json .
COPY pyproject.toml .
COPY requirements.txt .

# Copy additional necessary files if they exist
COPY generated_documents/ ./generated_documents/
COPY sdtm_workspace/ ./sdtm_workspace/

# Install the package in editable mode
RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LANGGRAPH_DEFAULT_RECURSION_LIMIT=250
ENV LANGGRAPH_RECURSION_LIMIT=250

# Expose LangGraph API port and file server port
EXPOSE 8123
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8123/ok || exit 1

# Default command - run LangGraph server
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "8123", "--no-browser"]
