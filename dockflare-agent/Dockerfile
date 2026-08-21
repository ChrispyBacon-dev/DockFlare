FROM python:3.11.6-slim

ARG DOCKFLARE_UID=65532
ARG DOCKFLARE_GID=65532

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

RUN addgroup --system --gid ${DOCKFLARE_GID} dockflare \
    && adduser --system --uid ${DOCKFLARE_UID} --ingroup dockflare dockflare \
    && mkdir -p /app/data \
    && chown -R dockflare:dockflare /app

USER dockflare:dockflare

CMD ["python", "main.py"]
