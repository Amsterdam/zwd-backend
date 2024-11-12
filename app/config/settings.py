"""
Django settings for zwd project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from os.path import join
from pathlib import Path


from config.logging import create_logging_config, setup_azure_monitor

from .azure_settings import Azure
from azure.identity import WorkloadIdentityCredential

azure = Azure()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "insecure")

ENVIRONMENT = os.getenv("ENVIRONMENT")
DEBUG = ENVIRONMENT == "local"

ALLOWED_HOSTS = ["*"]
DEFAULT_WORKFLOW_TYPE = os.getenv("DEFAULT_WORKFLOW_TYPE", "director")

# Application definition

INSTALLED_APPS = [
    "mozilla_django_oidc",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.cases",
    "apps.workflow",
    "apps.events",
    "apps.homeownerassociation",
    "apps.address",
    "django_spaghetti",
    "drf_spectacular",
    "django_celery_results",
]


LOCAL_DEVELOPMENT_AUTHENTICATION = (
    os.getenv("LOCAL_DEVELOPMENT_AUTHENTICATION", "False") == "True"
)

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "apps.users.auth.OIDCAuthenticationBackend",
]

SPAGHETTI_SAUCE = {
    "apps": ["cases", "workflow"],
    "show_fields": True,
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.auth.AuthenticationClass",
    ],
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "utils.exceptions.custom_exception_handler",
}

CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", ("http://default")).split(
    ","
)

SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]/",
    "TITLE": "ZWD Backend Gateway API",
    "VERSION": "v1",
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "mozilla_django_oidc.middleware.SessionRefresh",
]


OIDC_RP_CLIENT_ID = os.environ.get(
    "OIDC_RP_CLIENT_ID", "c622ea17-3c29-4b8f-ae84-56dda14419e7"
)
OIDC_OP_AUTHORIZATION_ENDPOINT = os.getenv(
    "OIDC_OP_AUTHORIZATION_ENDPOINT",
    "https://login.microsoftonline.com/72fca1b1-2c2e-4376-a445-294d80196804/oauth2/v2.0/authorize",
)
OIDC_OP_TOKEN_ENDPOINT = os.getenv(
    "OIDC_OP_TOKEN_ENDPOINT",
    "https://login.microsoftonline.com/72fca1b1-2c2e-4376-a445-294d80196804/oauth2/v2.0/token",
)
OIDC_OP_USER_ENDPOINT = os.getenv(
    "OIDC_OP_USER_ENDPOINT", "https://graph.microsoft.com/oidc/userinfo"
)
OIDC_OP_JWKS_ENDPOINT = os.getenv(
    "OIDC_OP_JWKS_ENDPOINT",
    "https://login.microsoftonline.com/72fca1b1-2c2e-4376-a445-294d80196804/discovery/v2.0/keys",
)
OIDC_RP_CLIENT_SECRET = os.environ.get("OIDC_RP_CLIENT_SECRET", None)

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


DATABASE_HOST = os.getenv("DATABASE_HOST", "database")
DATABASE_NAME = os.getenv("DATABASE_NAME", "dev")
DATABASE_USER = os.getenv("DATABASE_USER", "dev")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "dev")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_OPTIONS = {"sslmode": "allow", "connect_timeout": 5}

if "azure.com" in DATABASE_HOST:
    DATABASE_PASSWORD = azure.auth.db_password
    DATABASE_OPTIONS["sslmode"] = "require"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DATABASE_NAME,
        "USER": DATABASE_USER,
        "PASSWORD": DATABASE_PASSWORD,
        "HOST": DATABASE_HOST,
        "CONN_MAX_AGE": 60 * 5,
        "PORT": DATABASE_PORT,
    },
}


def get_redis_url():
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")
    REDIS_USERNAME = ""
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_PREFIX = "redis" if DEBUG else "rediss"

    return (
        f"{REDIS_PREFIX}://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
    )


CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
BROKER_URL = get_redis_url()
CELERY_BROKER_URL = get_redis_url()
BROKER_CONNECTION_MAX_RETRIES = None
BROKER_CONNECTION_TIMEOUT = 120
CELERY_TASK_TRACK_STARTED = True
CELERY_RESULT_BACKEND = "django-db"
CELERY_TASK_TIME_LIMIT = 30 * 60

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = os.path.normpath(join(os.path.dirname(BASE_DIR), "static"))

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "WARNING")

APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv(
    "APPLICATIONINSIGHTS_CONNECTION_STRING"
)
HAS_AZURE_LOGGING = True if APPLICATIONINSIGHTS_CONNECTION_STRING else False
LOGGING = create_logging_config()
if HAS_AZURE_LOGGING:
    setup_azure_monitor()

WORKFLOW_SPEC_CONFIG = {
    "default": {
        "process_vve_ok": {
            "initial_data": {"advice_type": {"value": "Default"}},
            "versions": {
                "1.0.0": {},
                "1.1.0": {},
                "1.2.0": {},
                "1.3.0": {},
            },
        },
    },
}

DSO_CLIENT_ID = os.getenv("DSO_CLIENT_ID", "default_client_id")
DSO_CLIENT_SECRET = os.getenv("DSO_CLIENT_SECRET", "default_client_secret")
DSO_AUTH_URL = os.getenv("DSO_AUTH_URL", "https://default.auth.url")
DSO_API_URL = os.getenv("DSO_API_URL", "https://default.api.url")


DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
AZURE_CONTAINER = os.getenv("AZURE_CONTAINER")
AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING", None)
AZURE_ACCOUNT_NAME = os.getenv("AZURE_ACCOUNT_NAME", None)

if DEBUG == False:
    AZURE_TOKEN_CREDENTIAL = WorkloadIdentityCredential()

if DEBUG:
    from azure.storage.blob import BlobServiceClient

    blob_service_client = BlobServiceClient.from_connection_string(
        AZURE_CONNECTION_STRING
    )
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER)
    if container_client.exists():
        print(f"Container '{AZURE_CONTAINER}' already exists, skipping creation.")
    else:
        blob_service_client.create_container(AZURE_CONTAINER)
        print(f"Container '{AZURE_CONTAINER}' created successfully.")
