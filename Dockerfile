FROM python:3.11-slim

LABEL org.opencontainers.image.title="Apex Multi Tools"
LABEL org.opencontainers.image.description="Interactive CLI framework for Linux Mint environment setup"
LABEL org.opencontainers.image.version="0.4.0-beta"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    sudo \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir rich pyyaml

# Copy framework
WORKDIR /opt/apex
COPY apex_framework.py .
COPY bootstrap.py .
COPY config/ config/
COPY apex_config.yaml .

# Make executable
RUN chmod +x apex_framework.py bootstrap.py

# Create non-root user
RUN useradd -m -s /bin/bash apex && \
    echo "apex ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER apex
WORKDIR /home/apex

ENTRYPOINT ["python3", "/opt/apex/apex_framework.py"]
CMD ["--help"]
