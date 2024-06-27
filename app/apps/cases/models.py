from django.db import models

# class Address(models.Model):
#     street = models.CharField(max_length=200)
#     city = models.CharField(max_length=100)
#     state = models.CharField(max_length=100)
#     postal_code = models.CharField(max_length=20)


# class HousingAssociation(models.Model):
#     name = models.CharField(max_length=100)
#     registration_number = models.CharField(max_length=50)
#     addresses = models.ManyToManyField(Address, related_name='cases')

class Case(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    # housing_association = models.ForeignKey(HousingAssociation, on_delete=models.CASCADE, related_name='cases')
