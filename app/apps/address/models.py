from django.db import models


class Address(models.Model):
    bag_id = models.CharField(max_length=255, null=False, unique=True)
