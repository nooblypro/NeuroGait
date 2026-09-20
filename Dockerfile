FROM 955519187785.dkr.ecr.ap-south-1.amazonaws.com/neurogait-ml:gate2

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy updated application source, models, scripts, tests, configuration, and test inputs
COPY src/ /app/src/
COPY models/ /app/models/
COPY scripts/ /app/scripts/
COPY tests/ /app/tests/
COPY pytest.ini /app/
COPY data/test_inputs/ /app/data/test_inputs/
COPY outputs/predictions/ /app/outputs/predictions/

# Ensure output directory exists
RUN mkdir -p /app/outputs

# Default entrypoint runs CLI inference help
CMD ["python3", "scripts/predict.py", "--help"]
