FROM python:3.13.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd -g 65532 mailmgr && \
    useradd -u 65532 -g mailmgr -m -s /bin/bash mailmgr

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY entrypoint.py .

RUN mkdir -p /data/attachments /data/db && \
    chown -R mailmgr:mailmgr /data

USER mailmgr

EXPOSE 8025

CMD ["python", "entrypoint.py"]
