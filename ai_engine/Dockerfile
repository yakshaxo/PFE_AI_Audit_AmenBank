FROM python:3.11-slim

WORKDIR /app

# Copy code
COPY . .

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir typing-inspect requests pandas matplotlib seaborn fpdf fastapi fastapi-utils uvicorn


# Expose FastAPI port
EXPOSE 5000

# Start the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
