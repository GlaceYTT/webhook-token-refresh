# Webhook Token Refresh Service
# For Java-only hosts - run this separately and call via webhook/cron
# Works on Render, Railway, and other Docker hosts
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including Xvfb for headless browser)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Clone youtube-trusted-session-generator for Python method
RUN mkdir -p /app/generator && \
    git clone https://github.com/iv-org/youtube-trusted-session-generator.git /app/generator && \
    # Patch extractor.py to force headless mode
    find /app/generator -name "extractor.py" -type f -exec sed -i 's/headless=False/headless=True/g' {} \; || true && \
    find /app/generator -name "*.py" -type f -exec sed -i 's/headless=False/headless=True/g' {} \; || true

# Install generator dependencies
RUN cd /app/generator && \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt || true; \
    fi

# Install playwright (required for token generation)
RUN pip install --no-cache-dir playwright && \
    python3 -m playwright install chromium && \
    python3 -m playwright install-deps chromium || true

# Copy webhook files
COPY webhook-token-refresh.py ./webhook-token-refresh.py

# Install webhook dependencies
RUN pip install --no-cache-dir requests flask

# Expose webhook port
EXPOSE 8000

# Run webhook service
CMD ["python3", "webhook-token-refresh.py"]
