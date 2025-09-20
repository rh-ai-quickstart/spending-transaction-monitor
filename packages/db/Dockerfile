FROM postgres:16-alpine

# Set environment variables
ENV POSTGRES_DB=spending-monitor
ENV POSTGRES_USER=user
ENV POSTGRES_PASSWORD=password

# Install python for running migration scripts
RUN apk add --no-cache python3 py3-pip

# Create a directory for the workspace
RUN mkdir -p /app

# Copy the db package
COPY . /app/packages/db/

WORKDIR /app/packages/db

# Install uv and dependencies for running migrations
RUN pip3 install --break-system-packages uv
RUN uv venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
RUN uv pip install -e .

# Copy initialization scripts
COPY src/db/scripts/ /docker-entrypoint-initdb.d/

# Add a script to run migrations after postgres starts
RUN echo '#!/bin/bash' > /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo 'set -e' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo '' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo '# Wait for postgres to be ready' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo 'until pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; do' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo '  echo "Waiting for postgres..."' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo '  sleep 2' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo 'done' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo '' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo '# Run alembic migrations' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo 'cd /app/packages/db' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo '/app/venv/bin/alembic upgrade head' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo '' >> /docker-entrypoint-initdb.d/99-run-migrations.sh && \
    echo 'echo "Database migrations completed"' >> /docker-entrypoint-initdb.d/99-run-migrations.sh

RUN chmod +x /docker-entrypoint-initdb.d/99-run-migrations.sh

EXPOSE 5432

# Use the default postgres entrypoint
CMD ["postgres"]