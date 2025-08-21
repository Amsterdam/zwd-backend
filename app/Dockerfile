FROM python:3.12-slim-bullseye
LABEL maintainer="datapunt@amsterdam.nl"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        libmagic1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_INSTALL_DIR=/root/.local/bin
ENV PATH="${UV_INSTALL_DIR}:$PATH"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY pyproject.toml uv.lock /app/

RUN uv venv "$VIRTUAL_ENV" \
    && uv sync --frozen --no-install-project

COPY . /app/

RUN chmod +x /app/celery.sh

ENTRYPOINT ["/app/deploy/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/app/config/config.ini"]
