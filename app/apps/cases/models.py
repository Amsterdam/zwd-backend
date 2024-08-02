from django.db import models


class Case(models.Model):
    description = models.TextField(null=True)


class CaseStateType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]
