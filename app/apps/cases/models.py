from typing import Iterable
from django.db import models
from .tasks import task_create_case

# class Address(models.Model):
#     street = models.CharField(max_length=200)
#     city = models.CharField(max_length=100)
#     state = models.CharField(max_length=100)
#     postal_code = models.CharField(max_length=20)


# class Vve(models.Model):
#     vve_statutaire_naam = models.TextField()


class Case(models.Model):
    description = models.TextField()

    def save(self, *args, **kwargs):
        task_create_case.delay(self.description)
        super().save(*args, **kwargs)
