# Zenith AI - Cloud Run Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build frontend and move to static directory
WORKDIR /app/frontend
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && npm install \
    && npm run build \
    && mkdir -p /app/static \
    && cp -r dist/* /app/static/ \
    && apt-get purge -y nodejs npm \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /app/frontend/node_modules
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 zenith && chown -R zenith:zenith /app
USER zenith

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
