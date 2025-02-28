FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/loan_request/ /app/services/loan_request/
COPY common/ /app/common/

# Set environment variables
ENV PYTHONPATH=/app

# Run the service
CMD ["uvicorn", "services.loan_request.api:app", "--host", "0.0.0.0", "--port", "8000"] 