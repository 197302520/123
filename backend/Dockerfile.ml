FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY config ./config
COPY learning ./learning
RUN pip install --no-cache-dir ".[ml]"
COPY . .
CMD ["celery", "-A", "config", "worker", "--loglevel=info", "--concurrency=1", "--queues=ml"]
