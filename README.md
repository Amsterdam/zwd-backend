# Zaken Woningkwaliteit Duurzaamheid (ZWD)
TODO

## Prerequisites

Make sure you have Docker installed locally:

- [Docker](https://docs.docker.com/docker-for-mac/install/)

## Getting up and running (Local development only)

These steps are necessary to make sure all configurations are set up correctly so that you can get the project running correctly.

First, make sure you have built the project and executed the database migrations:

```bash
docker network create zwd_network
docker-compose -f docker-compose.local.yml build
```

Start ZWD backend:

```bash
docker-compose -f docker-compose.local.yml up
```

Visit the Admin at http://localhost:8081/admin/


If you want to make use of the DSO api the following vars need to be set in the .local.env file:

```bash
DSO_API_URL=<url>
DSO_CLIENT_SECRET=<key>
DSO_AUTH_URL=<key>
DSO_API_URL=<key>
```



## Swagger

http://localhost:8081/api/schema/swagger/

## Django DB migrations

For changes to the model you have to migrate the DB.

```bash
python manage.py makemigrations --name <name_of_your_migration> <name_of_apps>

python manage.py migrate
```

name_of_apps is the model you would like to change like: cases, events, workflow or schedules.
You can use the `---empty` flag to create a custom migration.

## Adding pre-commit hooks

You can add pre-commit hooks for checking and cleaning up your changes:

```bash
bash bin/install_pre_commit.sh
```


## Running tests

Containers should be running to run tests via docker.
```bash
docker compose -f docker-compose.local.yml -f docker-compose.override.yml up -d
docker compose exec -T zwd-backend python manage.py test /app/apps
```
