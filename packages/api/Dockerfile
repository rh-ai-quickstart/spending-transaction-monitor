FROM registry.access.redhat.com/ubi9/python-312:latest

USER root

# Set working directory
WORKDIR /app

# Install system dependencies for PostgreSQL
RUN dnf install -y gcc gcc-c++ postgresql-devel && dnf clean all

# Create packages directory structure
RUN mkdir -p /app/packages/api /app/packages/db

# Copy the API package (context is root)
COPY packages/api/ ./packages/api/

# Copy the db package (context is root)
COPY packages/db/ ./packages/db/

# Install Python dependencies
# Install DB package first (dependency)
RUN pip install --no-cache-dir -e ./packages/db
# Then install API package with dev dependencies
RUN pip install --no-cache-dir -e ./packages/api[dev]
# Install psycopg2 for PostgreSQL sync operations (migrations)
RUN pip install --no-cache-dir psycopg2

# Set environment variables
ENV PYTHONPATH=/app/packages/api/src

USER 1001

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
WORKDIR /app/packages/api
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]