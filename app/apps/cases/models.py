from django.db import models
from apps.homeownerassociation.models import HomeownerAssociation
from apps.events.models import CaseEvent, ModelEventEmitter
from enum import Enum


class AdviceType(Enum):
    ENERGY_ADVICE = "Energieadvies"
    HBO = "Haalbaarheidsonderzoek"
    COURSE = "Cursus"

    @classmethod
    def choices(cls):
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
