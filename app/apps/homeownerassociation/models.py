from django.db import models, transaction
from clients.dso_client import DsoClient
from collections import Counter


class District(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Stadsdeel"
        verbose_name_plural = "Stadsdelen"
        ordering = ["name"]


class Neighborhood(models.Model):
    name = models.CharField(max_length=255)
    district = models.ForeignKey(
        District, related_name="neighborhoods", on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ("name", "district")
        verbose_name = "Buurt"
        verbose_name_plural = "Buurten"
        ordering = ["name"]


class Wijk(models.Model):
    name = models.CharField(max_length=255)
    neighborhood = models.ForeignKey(
        Neighborhood, related_name="wijken", on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Wijk"
        verbose_name_plural = "Wijken"
        ordering = ["name"]


class PriorityZipCode(models.Model):
    zip_code = models.CharField(max_length=6, unique=True)

    class Meta:
        verbose_name = "Prioriteitsbuurt postcode"
        verbose_name_plural = "Prioriteitsbuurt postcodes"
        ordering = ["zip_code"]


class HomeownerAssociation(models.Model):
    name = models.CharField(max_length=255, unique=True)
    build_year = models.IntegerField()
    number_of_appartments = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    zip_code = models.CharField(max_length=255, null=True)
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
    wijk = models.ForeignKey(
        Wijk,
        related_name="homeowner_associations",
        on_delete=models.DO_NOTHING,
        null=True,
    )
    monument_status = models.CharField(max_length=255, null=True)
    ligt_in_beschermd_gebied = models.CharField(max_length=255, null=True)
    beschermd_stadsdorpsgezicht = models.CharField(max_length=255, null=True)

    @property
    def is_small(self):
        return self.number_of_appartments <= 12

    @property
    def has_major_shareholder(self):
        for owner in self.owners.all():
            if (
                owner.number_of_appartments / self.number_of_appartments >= 0.25
                and owner.type != "Natuurlijk persoon"
            ):
                return True
        return False

    @property
    def is_priority_neighborhood(self):
        return PriorityZipCode.objects.filter(zip_code=self.zip_code).exists()

    def __str__(self):
        return self.name

    def get_or_create_hoa_by_bag_id(self, bag_id):
        client = DsoClient()
        hoa_name = client.get_hoa_name_by_bag_id(bag_id)
        existing_hoa = HomeownerAssociation.objects.filter(name=hoa_name).first()
        if existing_hoa:
            return existing_hoa

        distinct_hoa_response = client.get_hoa_by_name(hoa_name)

        district, neighborhood, wijk = self._get_district_and_neighborhood_and_wijk(
            distinct_hoa_response
        )
        with transaction.atomic():
            model = HomeownerAssociation.objects.create(
                name=hoa_name,
                build_year=distinct_hoa_response[0].get("pndOorspronkelijkBouwjaar"),
                number_of_appartments=len(distinct_hoa_response),
                district=district,
                neighborhood=neighborhood,
                wijk=wijk,
                zip_code=distinct_hoa_response[0].get("postcode"),
                monument_status=distinct_hoa_response[0].get("mntMonumentstatus"),
                ligt_in_beschermd_gebied=distinct_hoa_response[0].get(
                    "bsdLigtInBeschermdGebied"
                ),
                beschermd_stadsdorpsgezicht=distinct_hoa_response[0].get(
                    "bsdBeschermdStadsdorpsgezicht"
                ),
            )

            self._create_ownerships(distinct_hoa_response, model)
            return model

    def update_hoa_admin(self, hoa_name):
        client = DsoClient()
        distinct_hoa_response = client.get_hoa_by_name(hoa_name)
        district, neighborhood, wijk = self._get_district_and_neighborhood_and_wijk(
            distinct_hoa_response
        )

        self.build_year = distinct_hoa_response[0].get("pndOorspronkelijkBouwjaar")
        self.zip_code = distinct_hoa_response[0].get("postcode")
        self.monument_status = distinct_hoa_response[0].get("mntMonumentstatus")
        self.ligt_in_beschermd_gebied = distinct_hoa_response[0].get(
            "bsdLigtInBeschermdGebied"
        )
        self.beschermd_stadsdorpsgezicht = distinct_hoa_response[0].get(
            "bsdBeschermdStadsdorpsgezicht"
        )
        self.number_of_appartments = len(distinct_hoa_response)
        self.district = district
        self.neighborhood = neighborhood
        self.wijk = wijk

        self.save()

        self._create_ownerships(distinct_hoa_response, self)

    def _get_district_and_neighborhood_and_wijk(self, distinct_hoa_response):
        district, created = District.objects.get_or_create(
            name=distinct_hoa_response[0].get("gbdSdlNaam", "Onbekend")
        )
        neighborhood, created = Neighborhood.objects.get_or_create(
            name=distinct_hoa_response[0].get("gbdBrtNaam", "Onbekend"),
            district=district,
        )
        wijk, created = Wijk.objects.get_or_create(
            name=distinct_hoa_response[0].get("gbdWijkNaam", "Onbekend"),
            neighborhood=neighborhood,
        )
        return district, neighborhood, wijk

    def _create_ownerships(self, hoa_response, hoa_obj):
        ownership_counts = Counter(
            (address.get("eigCategorieEigenaar"), address.get("brkStatutaireNaam"))
            for address in hoa_response
            if "eigCategorieEigenaar" in address and "brkStatutaireNaam" in address
        )

        for (owner_type, owner_name), count in ownership_counts.items():
            owner, created = Owner.objects.get_or_create(
                type=owner_type if owner_type is not None else "Onbekend",
                name=owner_name if owner_name is not None else "Onbekend",
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

    def __str__(self):
        return self.email

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

    class Meta:
        ordering = ["email"]


class Owner(models.Model):
    type = models.CharField(max_length=255)
    name = models.CharField(max_length=255, null=True)
    number_of_appartments = models.IntegerField()
    homeowner_association = models.ForeignKey(
        HomeownerAssociation, related_name="owners", on_delete=models.DO_NOTHING
    )
