FROM python:3.11.6-slim

ARG DOCKFLARE_UID=65532
ARG DOCKFLARE_GID=65532

WORKDIR /app

ENV HEALTH_CHECK_PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

RUN addgroup --system --gid ${DOCKFLARE_GID} dockflare \
    && adduser --system --uid ${DOCKFLARE_UID} --ingroup dockflare dockflare \
    && mkdir -p /app/data \
    && chown -R dockflare:dockflare /app

USER dockflare:dockflare

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('HEALTH_CHECK_PORT', '8080') + '/health', timeout=3)"

CMD ["python", "main.py"]
