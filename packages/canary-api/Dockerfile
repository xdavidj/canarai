# Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies into a virtual environment
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache .

# Runtime stage
FROM python:3.11-slim AS runtime

# Create non-root user
RUN groupadd --gid 1000 canary && \
    useradd --uid 1000 --gid canary --shell /bin/bash --create-home canary

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source and alembic config
COPY src/ src/
COPY alembic.ini .

# Set environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# Switch to non-root user
USER canary

EXPOSE 8787

CMD ["uvicorn", "canary_api.main:app", "--host", "0.0.0.0", "--port", "8787"]
