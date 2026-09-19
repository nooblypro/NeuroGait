FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install native OS dependencies required by OpenCV and MediaPipe headless runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libegl1 \
    libgles2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source, models, scripts, tests, configuration, and data
COPY src/ /app/src/
COPY models/ /app/models/
COPY scripts/ /app/scripts/
COPY tests/ /app/tests/
COPY pytest.ini /app/
COPY data/ /app/data/

# Ensure output directory exists
RUN mkdir -p /app/outputs

# Default entrypoint runs CLI inference help
CMD ["python3", "scripts/predict.py", "--help"]
