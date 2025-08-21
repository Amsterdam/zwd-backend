FROM python:3.13-slim-trixie
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
ENV UV_LINK_MODE=copy
ENV PATH="${UV_INSTALL_DIR}:$PATH"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY . /app/

# Export dependencies to a requirements.txt file so we prevent from having
# to use a uv venv, and having to use `uv --active` for every python command.
# This is a workaround for the fact that uv doesn't support installing
# dependencies into the system interpreter.
RUN uv export --frozen --format requirements-txt > /tmp/req.txt
RUN uv pip install --system -r /tmp/req.txt

RUN chmod +x /app/celery.sh

ENTRYPOINT ["/app/deploy/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/app/config/config.ini"]
