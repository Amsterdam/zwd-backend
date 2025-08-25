FROM python:3.13-slim-trixie
LABEL maintainer="datapunt@amsterdam.nl"

ENV PYTHONUNBUFFERED=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_VERSION=2.1

RUN apt-get update && apt-get install -y \
  libpq-dev \
  gcc \
  libmagic1

RUN pip install --upgrade pip
RUN pip install setuptools
RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry install --no-interaction --no-ansi --no-root --with dev

COPY . /app/

RUN chmod +x /app/celery.sh

ENTRYPOINT ["/app/deploy/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/app/config/config.ini"]
