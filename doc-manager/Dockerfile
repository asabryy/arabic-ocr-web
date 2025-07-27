# Dockerfile.worker
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock* requirements.txt* /app/
RUN pip install --upgrade pip && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Copy app code
COPY . /app/

# Environment variable file (optional for local dev)
ENV PYTHONUNBUFFERED=1

# Start the consumer
CMD ["python", "app/worker/consumer.py"]
