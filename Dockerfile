# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# Use an official Python runtime as a parent image
# Using slim variant for smaller size
FROM python:3.13-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for downloading and installing cloudflared
# Also install cloudflared itself
# Pinning the version is recommended for reproducibility
# renovate: datasource=github-releases depName=cloudflare/cloudflared versioning=semver
ENV CLOUDFLARED_VERSION="2024.1.5"
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    # Clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    # Dynamically determine architecture and download the appropriate cloudflared binary
    && ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        CLOUDFLARED_ARCH="linux-amd64"; \
    elif [ "$ARCH" = "arm64" ]; then \
        CLOUDFLARED_ARCH="linux-arm64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    wget -q https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-$CLOUDFLARED_ARCH.deb && \
    dpkg -i cloudflared-$CLOUDFLARED_ARCH.deb && \
    rm cloudflared-$CLOUDFLARED_ARCH.deb && \
    cloudflared --version && \
    mkdir -p /root/.cloudflared && \
    echo "Created /root/.cloudflared directory" # Optional: confirmation log

# Install Python dependencies
# Copy requirements file first to leverage Docker cache
COPY requirements.txt .
# Install packages specified in requirements.txt
# --no-cache-dir reduces layer size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# In this case, just app.py
COPY app.py .

COPY templates /app/templates
COPY images /app/static/images
# Inform Docker that the container listens on port 5000 at runtime
# This is documentation; actual mapping is done in docker-compose.yml or `docker run -p`
EXPOSE 5000

# Define the command to run the application when the container starts
# It runs the Flask development server defined in app.py
# Environment variables (like CF_API_TOKEN) are expected to be passed in at runtime (e.g., via docker-compose)
CMD ["python", "app.py"]