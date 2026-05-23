FROM python:3.12-slim

# Install system dependencies including LibreOffice for headless rendering
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    libmagic1 \
    curl \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp directory for rendering
RUN mkdir -p /tmp/resumeos

# Non-root user for security
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app /tmp/resumeos
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
