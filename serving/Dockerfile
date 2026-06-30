# Containerizes the PipelineWatch FastAPI analytics dashboard.
# The image runs the live app (queries Gold marts via Athena).
# Credentials are provided at runtime via environment variables /
# an attached IAM role — never baked into the image.

FROM python:3.12-slim

# System deps kept minimal; no build tools needed for these wheels.
WORKDIR /app

# Install Python dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY app/ ./app/

# The app reads config from the environment (region, S3 staging, database).
# AWS credentials come from the runtime environment or an attached role.
ENV AWS_REGION=ap-south-1 \
    GLUE_DATABASE=pipelinewatch_gold

EXPOSE 8000

# Production server: uvicorn serving the FastAPI app.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
