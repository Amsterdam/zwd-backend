from django.db import models
from clients.dso_client import DsoClient


class HomeownerAssociation(models.Model):
    name = models.CharField(max_length=255, unique=True)
    build_year = models.IntegerField()
    number_of_appartments = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_or_create_hoa_by_bag_id(bag_id):
        client = DsoClient()
        hoa_name = client.get_hoa_name_by_bag_id(bag_id)
        # Check if the HomeownerAssociation already exists in the database
        existing_hoa = HomeownerAssociation.objects.filter(name=hoa_name).first()
        if existing_hoa:
            return existing_hoa

        hoa_response = client.get_hoa_by_name(hoa_name)
        distinct_hoa_response = list(
            {hoa["votIdentificatie"]: hoa for hoa in hoa_response}.values()
        )
        model = HomeownerAssociation.objects.create(
            name=hoa_name,
            build_year=distinct_hoa_response[0].get("pndOorspronkelijkBouwjaar"),
            number_of_appartments=len(distinct_hoa_response),
        )
        return model


class Contact(models.Model):
    homeowner_associations = models.ManyToManyField(
        HomeownerAssociation, related_name="contacts", default=None
    )
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    fullname = models.CharField(max_length=255)
    role = models.CharField(max_length=255)

    def process_contacts(case, contacts):
        for contact in contacts:
            email = contact.get("email")
            if not email:
                continue
            contact_data = {
                "fullname": contact.get("fullname"),
                "email": email,
                "phone": contact.get("phone"),
                "role": contact.get("role"),
            }
            existing_contact, created = Contact.objects.get_or_create(
                email=email, defaults=contact_data
            )
            if not created:
                for key, value in contact_data.items():
                    setattr(existing_contact, key, value)
                existing_contact.save()

            existing_contact.homeowner_associations.add(case.homeowner_association)
