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
<<<<<<< HEAD
    description = models.TextField()

=======
    description = models.TextField(null=True)
    # housing_association = models.ForeignKey(HousingAssociation, on_delete=models.CASCADE, related_name='cases')
>>>>>>> 6a896e0 (wip)
    def save(self, *args, **kwargs):
        task_create_case.delay(self.description)
        super().save(*args, **kwargs)


class CaseStateType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]
