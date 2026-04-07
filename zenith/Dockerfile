# Zenith AI - Cloud Run Dockerfile
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend
COPY zenith/frontend/package*.json ./
RUN npm install --legacy-peer-deps

COPY zenith/frontend/ .
RUN npm run build

# Python runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY zenith/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY zenith/ .

# Copy built frontend assets
COPY --from=frontend-builder /frontend/dist ./static

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
