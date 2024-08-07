from django.db import models

from apps.events.models import CaseEvent, ModelEventEmitter


class Case(ModelEventEmitter):
    description = models.TextField(null=True)
    EVENT_TYPE = CaseEvent.TYPE_CASE

    def __str__(self):
        return f"Case: {self.id}"

    def __get_event_values__(self):
        return {"description": self.description}

    def __get_case__(self):
        return self


class CaseStateType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]
