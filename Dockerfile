# Use official Python 3.11-slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (required for ML & scientific libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project
# Note: .dockerignore will exclude secrets and cache
COPY . .

# Create directory for persistent audio storage
RUN mkdir -p /app/audio_cache

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

# Expose FastAPI port
EXPOSE 8000

# Healthcheck to ensure the container is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Start FastAPI server via module notation to ensure proper pathing
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
