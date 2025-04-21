# Use an official Python runtime as a parent image
# Using slim variant for smaller size
FROM python:3.9-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1  # Prevents python from writing pyc files
ENV PYTHONUNBUFFERED 1         # Prevents python from buffering stdout/stderr

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for downloading and installing cloudflared
# Also install cloudflared itself
# Pinning the version is recommended for reproducibility
# renovate: datasource=github-releases depName=cloudflare/cloudflared versioning=semver
ARG CLOUDFLARED_VERSION=2024.1.5 # Check for the latest stable version if desired
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    # Clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    # Download cloudflared binary for linux amd64
    && wget -q https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-amd64.deb \
    # Install the downloaded package
    && dpkg -i cloudflared-linux-amd64.deb \
    # If dpkg fails due to missing dependencies, uncomment the next line
    # && apt-get install -f -y --no-install-recommends \
    # Clean up the downloaded .deb file
    && rm cloudflared-linux-amd64.deb \
    # Verify cloudflared installation (optional but good practice)
    && cloudflared --version \
    # Create the default cloudflared directory to avoid path errors
    # This directory is expected by cloudflared even if cert.pem isn't used for API commands
    && mkdir -p /root/.cloudflared \
    && echo "Created /root/.cloudflared directory" # Optional: confirmation log

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
# Inform Docker that the container listens on port 5000 at runtime
# This is documentation; actual mapping is done in docker-compose.yml or `docker run -p`
EXPOSE 5000

# Define the command to run the application when the container starts
# It runs the Flask development server defined in app.py
# Environment variables (like CF_API_TOKEN) are expected to be passed in at runtime (e.g., via docker-compose)
CMD ["python", "app.py"]