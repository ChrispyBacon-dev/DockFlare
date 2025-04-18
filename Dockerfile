# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1  # Prevents Python from writing pyc files
ENV PYTHONUNBUFFERED 1         # Prevents Python from buffering stdout/stderr

# Set the working directory in the container
WORKDIR /app

# Install system dependencies and cloudflared (auto-detects architecture)
ARG CLOUDFLARED_VERSION=2024.1.5
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    && ARCH=$(dpkg --print-architecture) \
    && wget -q https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-${ARCH}.deb \
    && dpkg -i cloudflared-linux-${ARCH}.deb \
    && rm cloudflared-linux-${ARCH}.deb \
    && cloudflared --version \
    && mkdir -p /root/.cloudflared \
    && echo "Created /root/.cloudflared directory"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app.py .
COPY templates /app/templates

# Expose the port the app runs on
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]
