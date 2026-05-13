FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN DEBUG=True SECRET_KEY=collectstatic-build-key python manage.py collectstatic --noinput

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_data && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
