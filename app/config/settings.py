"""
Django settings for zwd project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path
from os.path import join
from .azure_settings import Azure


azure = Azure()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-p9v7bvv$nx#qmrxu(yl08=@zygn6mcc-r*xa5+@9p5-+%hvis)'

ENVIRONMENT = os.getenv("ENVIRONMENT")
DEBUG = ENVIRONMENT == "local"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.cases',
    'django_spaghetti',
    'drf_spectacular',
    'django_celery_results'
]

SPAGHETTI_SAUCE = {
    "apps": [
        "cases"
    ],
    "show_fields": True,
}

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]/",
    "TITLE": "Zaken Backend Gateway API",
    "VERSION": "v1",
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


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
    if "windows.net" in REDIS_HOST:
        REDIS_USERNAME = os.getenv("REDIS_USERNAME")
        REDIS_PASSWORD = "todo"
    return f"{REDIS_PREFIX}://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"

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
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.normpath(join(os.path.dirname(BASE_DIR), "static"))

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
