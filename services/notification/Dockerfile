FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY services/notification/requirements.txt ./services/notification/
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r services/notification/requirements.txt \
    && pip install fastapi uvicorn celery redis sse_starlette

# Copy project files
COPY common/ /app/common/
COPY services/notification/ /app/services/notification/

# Create non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the service
CMD ["uvicorn", "services.notification.api:app", "--host", "0.0.0.0", "--port", "8000"] 