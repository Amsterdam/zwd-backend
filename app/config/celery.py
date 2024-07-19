import os

from celery import Celery
from django.apps import apps

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("proj")
app.conf.task_default_queue = "ZWD"
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
