from django.db import models
from clients.dso_client import DsoClient
from collections import Counter


class District(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Neighborhood(models.Model):
    name = models.CharField(max_length=255)
    district = models.ForeignKey(
        District, related_name="neighborhoods", on_delete=models.DO_NOTHING
    )

    class Meta:
        unique_together = ("name", "district")


class HomeownerAssociation(models.Model):
    name = models.CharField(max_length=255, unique=True)
    build_year = models.IntegerField()
    number_of_appartments = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    district = models.ForeignKey(
        District,
        related_name="homeowner_associations",
        on_delete=models.DO_NOTHING,
        null=True,
    )
    neighborhood = models.ForeignKey(
        Neighborhood,
        related_name="homeowner_associations",
        on_delete=models.DO_NOTHING,
        null=True,
    )
    zip_code = models.CharField(max_length=255, null=True)

    @property
    def is_small(self):
        return self.number_of_appartments <= 12

    def get_or_create_hoa_by_bag_id(self, bag_id):
        client = DsoClient()
        hoa_name = client.get_hoa_name_by_bag_id(bag_id)
        existing_hoa = HomeownerAssociation.objects.filter(name=hoa_name).first()
        if existing_hoa:
            return existing_hoa

        hoa_response = client.get_hoa_by_name(hoa_name)
        distinct_hoa_response = self._get_distinct_hoa_response(hoa_response)
        district, neighborhood = self._get_district_and_neighborhood(
            distinct_hoa_response
        )

        model = HomeownerAssociation.objects.create(
            name=hoa_name,
            build_year=distinct_hoa_response[0].get("pndOorspronkelijkBouwjaar"),
            number_of_appartments=len(distinct_hoa_response),
            district=district,
            neighborhood=neighborhood,
            zip_code=distinct_hoa_response[0].get("postcode"),
        )

        self._create_ownerships(distinct_hoa_response, model)
        return model

    def update_hoa_admin(self, hoa_name):
        client = DsoClient()
        hoa_response = client.get_hoa_by_name(hoa_name)
        distinct_hoa_response = self._get_distinct_hoa_response(hoa_response)
        district, neighborhood = self._get_district_and_neighborhood(
            distinct_hoa_response
        )

        self.build_year = distinct_hoa_response[0].get("pndOorspronkelijkBouwjaar")
        self.number_of_appartments = len(distinct_hoa_response)
        self.zip_code = distinct_hoa_response[0].get("postcode")
        self.district = district
        self.neighborhood = neighborhood
        self.save()

        self._create_ownerships(distinct_hoa_response, self)

    def _get_distinct_hoa_response(self, hoa_response):
        return list({hoa["votIdentificatie"]: hoa for hoa in hoa_response}.values())

    def _get_district_and_neighborhood(self, distinct_hoa_response):
        district, created = District.objects.get_or_create(
            name=distinct_hoa_response[0].get("gbdSdlNaam", "Onbekend")
        )
        neighborhood, created = Neighborhood.objects.get_or_create(
            name=distinct_hoa_response[0].get("gbdBrtNaam", "Onbekend"),
            district=district,
        )
        return district, neighborhood

    def _create_ownerships(self, hoa_response, hoa_obj):
        ownership_counts = Counter(
            (address.get("eigCategorieEigenaar"), address.get("brkStatutaireNaam"))
            for address in hoa_response
            if "eigCategorieEigenaar" in address and "brkStatutaireNaam" in address
        )

        for (owner_type, owner_name), count in ownership_counts.items():
            owner, created = Owner.objects.get_or_create(
                type=owner_type,
                name=owner_name,
                homeowner_association=hoa_obj,
                number_of_appartments=count,
            )

            if not created:
                owner.number_of_appartments = count
                owner.save()


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


class Owner(models.Model):
    type = models.CharField(max_length=255)
    name = models.CharField(max_length=255, null=True)
    number_of_appartments = models.IntegerField()
    homeowner_association = models.ForeignKey(
        HomeownerAssociation, related_name="owners", on_delete=models.DO_NOTHING
    )
