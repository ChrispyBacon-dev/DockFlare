# Dockerfile located at GitRoot/dockflare/Dockerfile
# GitHub Action context: ./dockflare

# --- Frontend Builder Stage ---
FROM node:20-alpine as frontend-builder
LABEL stage=frontend-builder
WORKDIR /buildstage # Using a clear, distinct WORKDIR for this stage

# 1. Copy package files (package.json, etc., are at the root of the 'dockflare' context)
COPY package.json ./package.json
COPY package-lock.json* ./
RUN npm install

# 2. Copy Tailwind/PostCSS configs (also at the root of 'dockflare' context)
COPY tailwind.config.js ./tailwind.config.js
COPY postcss.config.js ./postcss.config.js

# 3. Create the 'app/templates' structure expected by the build script
#    and copy input.css and other templates into it.
#    'app/templates/input.css' is relative to 'dockflare' context root.
RUN mkdir -p ./app/templates
COPY app/templates/input.css ./app/templates/input.css
COPY app/templates ./app/templates # Copies content of context_root/app/templates

# 4. Run the build script. It executes in WORKDIR (/buildstage)
#    The script in package.json uses relative paths:
#    -c ./tailwind.config.js (finds /buildstage/tailwind.config.js)
#    -i ./app/templates/input.css (finds /buildstage/app/templates/input.css)
#    -o ./app/static/css/output.css (creates /buildstage/app/static/css/output.css)
RUN npm run build:css

# (Optional Debugging)
# RUN ls -R /buildstage

# --- Runtime Stage ---
FROM python:3.13-slim as runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app # Runtime WORKDIR
ENV CLOUDFLARED_VERSION="2024.1.5"
# ... (cloudflared install section - no changes) ...
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
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
    mkdir -p /root/.cloudflared

# requirements.txt is at the root of 'dockflare' context
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create static directories in the runtime image
RUN mkdir -p /app/static/css && mkdir -p /app/static/images

# Copy the generated CSS from the frontend-builder stage
# Source path is absolute within the builder stage
COPY --from=frontend-builder /buildstage/app/static/css/output.css /app/static/css/output.css

# Copy the Python application code (the 'app' directory is at root of 'dockflare' context)
COPY app /app

# Copy images (images/ is at root of 'dockflare' context)
COPY images /app/static/images/

EXPOSE 5000
CMD ["python", "main.py"]