# Development Dockerfile with hot reloading
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
COPY requirements-minimal.txt .

# Install Python dependencies with fallback
RUN pip install --no-cache-dir -r requirements.txt || \
    (echo "Full requirements failed, trying minimal requirements..." && \
     pip install --no-cache-dir -r requirements-minimal.txt)

# Copy application code
COPY . .

# Create directories for databases and ensure proper permissions
RUN mkdir -p /app/data /app/data/vector_db && chmod 755 /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:///./data/jedi_agent.db
ENV VECTOR_DB_PATH=./data/vector_db
ENV DEBUG=true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/')" || exit 1

# Run the application with auto-reload enabled
CMD ["python", "main.py", "serve"]
