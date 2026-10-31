FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

FROM base AS dsv

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS prd

ENV PORT=8000
ENV WEB_CONCURRENCY=2
ENV GUNICORN_CMD_ARGS="--threads 4 --timeout 60 --access-logfile -"

RUN DJANGO_ENV=dsv python manage.py collectstatic --noinput
RUN useradd --system app

USER app

CMD ["gunicorn", "config.wsgi:application"]
