# Webhook Token Refresh Service
# For Java-only hosts - run this separately and call via webhook/cron
# Works on Render, Railway, and other Docker hosts
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone youtube-trusted-session-generator for Python method
RUN mkdir -p /app/generator && \
    git clone https://github.com/iv-org/youtube-trusted-session-generator.git /app/generator

# Install generator dependencies
RUN cd /app/generator && \
    pip install --no-cache-dir -r requirements.txt 2>/dev/null || \
    pip install --no-cache-dir playwright && \
    python3 -m playwright install chromium

# Copy webhook files
COPY webhook-token-refresh.py ./webhook-token-refresh.py
COPY requirements.txt ./requirements.txt

# Install webhook dependencies
RUN pip install --no-cache-dir -r requirements.txt flask

# Expose webhook port
EXPOSE 8000

# Run webhook service
CMD ["python3", "webhook-token-refresh.py"]
