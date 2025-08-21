# Zaken Woningkwaliteit Duurzaamheid (ZWD)

De afdeling Woningkwaliteit en Duurzaamheid heeft als doel om de woningkwaliteit en duurzaamheid in Amsterdam te monitoren en te verbeteren. Om dit doel te bereiken, ondersteunen zij de Verenigingen van Eigenaren (vve’s), particulieren buiten vve’s, woningcorporaties, en vastgoedprofessionals. Door middel van dit zaaksysteem worden alle processen gestuurd en gemonitord.

## Prerequisites

Make sure you have Docker installed locally:

- [Docker](https://docs.docker.com/docker-for-mac/install/)

## Getting up and running (Local development only)

These steps are necessary to make sure all configurations are set up correctly so that you can get the project running correctly.

### Creating networks & build container

First, create a network and build the project:

```bash
docker network create zwd_network
docker-compose -f docker-compose.local.yml build
```

### Starting the backend

Run the following to start the backend:

```bash
docker-compose -f docker-compose.local.yml up
```

### Creating a superuser

For accessing the Django admin during local development you'll have to become a `superuser`. This user should have the same `email` and `username` as the one that will be auto-created by the SSO login.

Run the following command to either create the user, or make the existing one a superuser:

```bash
sh bin/setup_superuser.sh <email>
```

### Using local development authentication
To run the project with local Django authentication instead of OpenID Connect (OIDC), create a `.env.local` file with:

```bash
LOCAL_DEVELOPMENT_AUTHENTICATION=False
```

### Django admin

Visit the Admin at http://localhost:8081/admin/


### DSO API

If you want to make use of the DSO API, the following vars need to be set in the `.env.local` file:

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

## Dynamic values in BPMN field labels
The embedded form in the camunda task does not support dynamic values by default.
In the workflow model is a "method _evaluate_form_field_label" that will parse a form label with the following structure {{workflow.prop}}
``
<camunda:formData>
    <camunda:formField id="form_controle_bouwjaar" label="This is a sentence for case {{workflow.case.id}}" type="enum">
</camunda:formField>
``
The above label will be parsed to "This is a sentence for case 123"
Currently all properties and related objects of the workflow model are supported
