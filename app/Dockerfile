FROM python:3.12-slim-bullseye
LABEL maintainer="datapunt@amsterdam.nl"

RUN apt-get update && apt-get install -y
RUN apt-get install libpq-dev -y
RUN apt-get install gcc -y
RUN apt install libmagic1 -y
RUN pip install --upgrade pip
RUN pip install uwsgi
RUN pip install setuptools
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app/


RUN chmod +x /app/celery.sh

ENTRYPOINT ["/app/deploy/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/app/config/config.ini"]
