# Use an official Python runtime as a parent image
# Using slim variant for smaller size
FROM python:3.13-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for downloading and installing cloudflared
# renovate: datasource=github-releases depName=cloudflare/cloudflared versioning=semver
ENV CLOUDFLARED_VERSION="2024.1.5"

# Install dependencies in one step to keep the layer size down
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    nodejs \
    npm \
    # Clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    # Verify node and npm are installed correctly
    && nodejs --version \
    && npm --version \
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

# Create static directory if it doesn't exist and copy Tailwind CSS files
RUN mkdir -p /app/static
COPY static/ /app/static/
COPY tailwind.config.js /app/

# Install Tailwind CSS globally and build the CSS
RUN npm install -g tailwindcss postcss autoprefixer && \
    tailwindcss -c tailwind.config.js -i /app/static/main.css -o /app/static/tailwind.css --minify

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY app.py .
COPY templates /app/templates

# Inform Docker that the container listens on port 5000 at runtime
EXPOSE 5000

# Define the command to run the application when the container starts
CMD ["python", "app.py"]