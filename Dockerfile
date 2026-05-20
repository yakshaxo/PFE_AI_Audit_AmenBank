FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements from root to container
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 1. Copy the contents of the ai_engine folder into /app
COPY ai_engine/ .

# 2. Copy the templates folder from your project root into /app/templates
COPY templates/ ./templates/

# Ensure logs appear instantly
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]