FROM redis:6.2.14-alpine3.18

# Setup Certificates for ADP/Motiv
# Add the certificate to the Redis folder before deployment.
RUN apk update && \
    apk add --no-cache ca-certificates && \
    update-ca-certificates --fresh

RUN apk add --no-cache gettext
COPY redis.conf.template /usr/local/etc/redis/redis.conf.template

CMD envsubst < /usr/local/etc/redis/redis.conf.template > /usr/local/etc/redis/redis.conf && exec redis-server /usr/local/etc/redis/redis.conf
