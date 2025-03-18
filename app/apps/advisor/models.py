from django.db import models


class Advisor(models.Model):
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    advice_type_energieadvies = models.BooleanField(default=False)
    advice_type_hbo = models.BooleanField(default=False)
    small_hoa = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
