FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/credit_check/ /app/services/credit_check/
COPY common/ /app/common/

# Set environment variables
ENV PYTHONPATH=/app
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

# Run the service
CMD ["uvicorn", "services.credit_check.api:app", "--host", "0.0.0.0", "--port", "8000"] 