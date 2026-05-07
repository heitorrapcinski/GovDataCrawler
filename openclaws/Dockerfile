# OpenClaws AI Assistant - Containerized Python CLI
# Analyzes Brazilian government contract artifacts using IBM Granite LLM

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy project configuration and install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy the openclaws package
COPY openclaws/ ./openclaws/

# Reinstall to pick up the package source
RUN pip install --no-cache-dir .

# Create the legislation cache directory (writable volume mount point)
RUN mkdir -p /app/legislation_cache

# Document volume mounts:
# /app/target - read-only mount for contract artifacts from the target folder
# /app/legislation_cache - writable mount for cached legislation content
VOLUME ["/app/target", "/app/legislation_cache"]

# Set the entry point to run the openclaws CLI
ENTRYPOINT ["openclaws"]
