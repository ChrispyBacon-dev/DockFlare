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
# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
# (License header remains the same)
# --- Frontend Builder Stage ---
FROM node:20-alpine as frontend-builder
LABEL stage=frontend-builder
WORKDIR /build # Changed WORKDIR to something simple for this stage

# Copy files needed for the build from the 'dockflare' subdirectory of the build context
COPY ./dockflare/package.json ./package.json
COPY ./dockflare/package-lock.json* ./
COPY ./dockflare/tailwind.config.js ./tailwind.config.js
COPY ./dockflare/postcss.config.js ./postcss.config.js

# Create the expected directory structure for input.css and templates
# relative to the WORKDIR (/build)
RUN mkdir -p ./app/templates
COPY ./dockflare/app/templates/input.css ./app/templates/input.css
COPY ./dockflare/app/templates ./app/templates 

RUN npm install

RUN echo ">>> Current directory before npm run build:css is $(pwd)" && \
    echo ">>> Listing WORKDIR (/build) contents:" && \
    ls -la . && \
    echo ">>> Listing ./app/ contents:" && \
    ls -la ./app/ && \
    echo ">>> Listing ./app/templates/ contents:" && \
    ls -la ./app/templates/ && \
    echo ">>> Running npm run build:css..." && \
    npm run build:css

RUN echo ">>> CSS build supposedly complete. Verifying output..." && \
    echo ">>> Listing /build/app/ :" && \
    ls -la /build/app/ && \
    echo ">>> Listing /build/app/static/ :" && \
    ls -la /build/app/static/ && \
    echo ">>> Listing /build/app/static/css/ :" && \
    ls -la /build/app/static/css/ && \
    echo ">>> Checking for /build/app/static/css/output.css existence:" && \
    (test -f /build/app/static/css/output.css && echo "output.css FOUND" || echo "output.css NOT FOUND")
# End of frontend-builder stage

# --- Runtime Stage ---
FROM python:3.13-slim as runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
ENV CLOUDFLARED_VERSION="2024.1.5"
# ... (cloudflared install) ...
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

COPY ./dockflare/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=frontend-builder /build/app/static/css/output.css /app/static/css/output.css

COPY ./dockflare/app /app
COPY ./images /app/static/images/
EXPOSE 5000
CMD ["python", "main.py"]