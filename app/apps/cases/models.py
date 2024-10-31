from django.db import models
from apps.homeownerassociation.models import HomeownerAssociation
from apps.events.models import CaseEvent, ModelEventEmitter
from enum import Enum
import os
from apps.events.models import CaseEvent, ModelEventEmitter
from django.core.files.storage import default_storage


class AdviceType(Enum):
    ENERGY_ADVICE = "Energieadvies"
    HBO = "Haalbaarheidsonderzoek"
    COURSE = "Cursus"

    @classmethod
    def choices(cls):
        [(key.value, key.name) for key in cls]
        return [(key.value, key.name) for key in cls]


class Case(ModelEventEmitter):
    description = models.TextField(null=True)
    advice_type = models.CharField(
        choices=AdviceType.choices(), default=AdviceType.COURSE.value
    )
    EVENT_TYPE = CaseEvent.TYPE_CASE
    homeowner_association = models.ForeignKey(
        HomeownerAssociation, on_delete=models.CASCADE, related_name="cases", null=True
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Case: {self.id}"

    def __get_event_values__(self):
        return {"description": self.description, "advice_type": self.advice_type}

    def __get_case__(self):
        return self


class CaseStateType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]


def get_upload_path(instance, filename):
    return os.path.join("uploads", "cases", "%s" % instance.case.id, filename)


class CaseDocument(models.Model):
    name = models.CharField(max_length=100)
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="documents")
    document = models.FileField(upload_to=get_upload_path)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document: {self.id}"

    def delete(self):
        default_storage.delete(self.document.name)
        return super().delete()
