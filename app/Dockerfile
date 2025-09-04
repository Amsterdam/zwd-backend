FROM python:3.13-slim-trixie
LABEL maintainer="datapunt@amsterdam.nl"

ENV PYTHONUNBUFFERED=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_VERSION=2.1.4

RUN apt-get update && apt-get install -y \
  libpq-dev \
  gcc \
  libmagic1 \
  media-types \
  tzdata \
  wget \
  curl \
  netcat-openbsd \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools uwsgi
RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry install --no-interaction --no-ansi --no-root

COPY . /app/

RUN chmod +x /app/celery.sh

ENTRYPOINT ["/app/deploy/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/app/config/config.ini"]
