from django.utils import timezone
from django.conf import settings
from django.db import models, transaction
from apps.advisor.models import Advisor
from apps.homeownerassociation.models import HomeownerAssociation
from apps.events.models import CaseEvent, ModelEventEmitter
from enum import Enum
import os
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
    description = models.TextField(null=True, blank=True)
    advice_type = models.CharField(
        choices=AdviceType.choices(), default=AdviceType.COURSE.value
    )
    EVENT_TYPE = CaseEvent.TYPE_CASE
    homeowner_association = models.ForeignKey(
        HomeownerAssociation, on_delete=models.CASCADE, related_name="cases", null=True
    )
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="case_author",
        on_delete=models.PROTECT,
        null=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    end_date = models.DateField(null=True, blank=True)
    advisor = models.ForeignKey(
        to=Advisor,
        related_name="case_advisor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    legacy_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    status = models.ForeignKey(
        to="cases.CaseStateType",
        related_name="cases_status",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def close_case(self):
        with transaction.atomic():
            self.workflows.all().delete()
            self.end_date = timezone.datetime.now()
            self.save()

    def __str__(self):
        return f"Case: {self.id}"

    def __get_event_values__(self):
        return {
            "description": self.description,
            "advice_type": self.advice_type,
            "author": self.author.__str__(),
            "date_added": self.created,
        }

    def __get_case__(self):
        return self

    class Meta:
        ordering = ["-id"]


class CaseStateType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]
        verbose_name = "Status"
        verbose_name_plural = "Statuses"


def get_upload_path(instance, filename):
    return os.path.join("uploads", "cases", "%s" % instance.case.id, filename)


class CaseDocument(models.Model):
    name = models.CharField(max_length=100)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="documents")
    document = models.FileField(upload_to=get_upload_path)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document: {self.id}"

    def delete(self):
        default_storage.delete(self.document.name)
        return super().delete()

    class Meta:
        verbose_name = "Document"
