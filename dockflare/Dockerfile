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
FROM node:20-alpine as frontend-builder
LABEL stage=frontend-builder
WORKDIR /usr/src/app # Build context for this stage
COPY package.json package-lock.json* ./
RUN npm install
COPY tailwind.config.js postcss.config.js ./
COPY ./app ./app
RUN npm run build:css
FROM python:3.13-slim as runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app # This will be the application root in the final image
ENV CLOUDFLARED_VERSION="2024.1.5"
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
    wget -q "https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-${CLOUDFLARED_ARCH}.deb" && \
    dpkg -i "cloudflared-${CLOUDFLARED_ARCH}.deb" && \
    rm "cloudflared-${CLOUDFLARED_ARCH}.deb" && \
    cloudflared --version && \
    mkdir -p /root/.cloudflared

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=frontend-builder /usr/src/app/app/static/css/output.css /app/static/css/output.css
COPY ./app /app
EXPOSE 5000
CMD ["python", "main.py"]