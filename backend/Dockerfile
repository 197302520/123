FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY config ./config
COPY learning ./learning
RUN pip install --no-cache-dir .
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_learning_content && python manage.py runserver 0.0.0.0:8000"]
