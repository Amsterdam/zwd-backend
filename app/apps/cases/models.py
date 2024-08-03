from django.db import models

from .tasks import task_create_case

class Case(models.Model):
    description = models.TextField(null=True)

    def save(self, *args, **kwargs):
        task_create_case.delay(self.description)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Case: {self.id}"


class CaseStateType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]
