# Production Dockerfile for DEAN Orchestrator
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt ./
COPY requirements/ ./requirements/
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY configs/ ./configs/

# Create non-root user
RUN useradd -m -u 1000 dean && chown -R dean:dean /app
USER dean

# Set environment variables
ENV PYTHONPATH=/app/src:$PYTHONPATH
ENV DEAN_ENV=production
ENV DEAN_SERVER_HOST=0.0.0.0
ENV DEAN_SERVER_PORT=8082

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Run the application using the dean-server command from pyproject.toml
CMD ["python", "-m", "dean_orchestration.server"]