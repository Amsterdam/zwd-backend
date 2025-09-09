from django.utils import timezone
from django.conf import settings
from django.db import models, transaction
from apps.advisor.models import Advisor
from apps.homeownerassociation.models import HomeownerAssociation
from apps.events.models import CaseEvent, ModelEventEmitter, TaskModelEventEmitter
from enum import Enum
import os
from django.core.files.storage import default_storage


class ApplicationType(Enum):
    ADVICE = "Advies"
    ACTIVATIONTEAM = "Activatieteam"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class AdviceType(Enum):
    ENERGY_ADVICE = "Energieadvies"
    HBO = "Haalbaarheidsonderzoek"
    COURSE = "Cursus"

    @classmethod
    def choices(cls):
        [(key.value, key.name) for key in cls]
        return [(key.value, key.name) for key in cls]


class CaseStatus(models.Model):
    name = models.CharField(max_length=255, unique=True)
    position = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["position"]
        verbose_name = "Status"
        verbose_name_plural = "Statuses"


class Case(ModelEventEmitter):
    EVENT_TYPE = CaseEvent.TYPE_CASE
    application_type = models.CharField(
        choices=ApplicationType.choices(), default=ApplicationType.ADVICE.value
    )
    advice_type = models.CharField(choices=AdviceType.choices(), blank=True, null=True)
    status = models.ForeignKey(
        to=CaseStatus,
        related_name="cases_status",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    homeowner_association = models.ForeignKey(
        HomeownerAssociation, on_delete=models.CASCADE, related_name="cases", null=True
    )
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="case_author",
        on_delete=models.PROTECT,
        null=True,
    )
    created = models.DateTimeField(default=timezone.now)
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
    description = models.TextField(null=True, blank=True)
    prefixed_dossier_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )

    def _compute_prefixed_dossier_id(self):
        if self.application_type == ApplicationType.ACTIVATIONTEAM.value:
            return f"{self.id}ACT"

        if self.advice_type == AdviceType.COURSE.value:
            return f"{self.id}CUR"
        if self.advice_type == AdviceType.HBO.value:
            return f"{self.id}HBO"
        if self.advice_type == AdviceType.ENERGY_ADVICE.value:
            if self.homeowner_association and self.homeowner_association.is_small:
                return f"{self.id}EAK"
            else:
                return f"{self.id}EAG"

        return str(self.id)

    def save(self, *args, **kwargs):
        is_create = self.pk is None
        result = super().save(*args, **kwargs)
        if is_create and not self.prefixed_dossier_id:
            self.prefixed_dossier_id = self._compute_prefixed_dossier_id()
            super(Case, self).save(update_fields=["prefixed_dossier_id"])
        return result

    def close_case(self):
        with transaction.atomic():
            self.workflows.all().delete()
            self.end_date = timezone.datetime.now()
            self.save()

    def __str__(self):
        return f"Case: {self.id}"

    def __get_event_values__(self):
        values = {
            "application_type": self.application_type,
            "author": str(self.author) if self.author else None,
            "date_added": self.created,
            "description": self.description,
        }
        if self.application_type == ApplicationType.ADVICE.value:
            values["advice_type"] = self.advice_type

        if hasattr(self, "activation_team"):
            values["activation_team_type"] = (self.activation_team.type,)
            values["activation_team_subject"] = self.activation_team.subject
            values["activation_team_meeting_date"] = self.activation_team.meeting_date

        return values

    def __get_case__(self):
        return self

    class Meta:
        ordering = ["-id"]


class ActivationTeamType(Enum):
    INFORMATIEBIJEENKOMST = "Informatiebijeenkomst"
    LEDENVERGADERING = "Ledenvergadering"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class ActivationTeam(models.Model):
    case = models.OneToOneField(
        Case, on_delete=models.CASCADE, related_name="activation_team"
    )
    type = models.CharField(
        choices=ActivationTeamType.choices(),
        default=ActivationTeamType.INFORMATIEBIJEENKOMST.value,
    )
    subject = models.TextField(null=True, blank=True)
    meeting_date = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Activatieteam"


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


class CaseCloseReason(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_successful = models.BooleanField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class CaseClose(TaskModelEventEmitter):
    EVENT_TYPE = CaseEvent.TYPE_CASE_CLOSE
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    reason = models.ForeignKey(CaseCloseReason, on_delete=models.PROTECT)
    description = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="case_close_author",
        on_delete=models.PROTECT,
        null=True,
    )

    def __str__(self):
        return f"Case: {self.case.id} - {self.reason.name}"

    def __get_event_values__(self):
        event_values = {
            "date_added": self.created,
            "author": str(self.author) if self.author else None,
            "reason": self.reason.name,
            "description": self.description,
        }
        return event_values

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.case.close_case()
            self.case.status, _ = CaseStatus.objects.get_or_create(name="Afgesloten")
            self.case.save()
            return super().save(*args, **kwargs)
