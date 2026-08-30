FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["granian", "--interface", "wsgi", "config.wsgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
