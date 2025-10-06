from apps.homeownerassociation.models import (
    Contact,
    District,
    HomeownerAssociation,
    Neighborhood,
    Owner,
    Wijk,
)
from rest_framework import serializers


class NeighborhoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Neighborhood
        fields = ["id", "name"]


class DistrictSerializer(serializers.ModelSerializer):
    neighborhoods = NeighborhoodSerializer(many=True, read_only=True)

    class Meta:
        model = District
        fields = ["id", "name", "neighborhoods"]
        depth = 1


class WijkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wijk
        fields = ["id", "name"]
        depth = 1


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = [
            "type",
            "name",
            "number_of_apartments",
        ]
        depth = 1


class HomeownerAssociationSerializer(serializers.ModelSerializer):
    district = serializers.SerializerMethodField()
    neighborhood = serializers.SerializerMethodField()
    wijk = serializers.SerializerMethodField()
    is_small = serializers.BooleanField()
    is_priority_neighborhood = serializers.BooleanField()
    owners = OwnerSerializer(many=True, required=False)

    def get_district(self, obj):
        if not obj.district:
            return None
        return obj.district.name

    def get_neighborhood(self, obj):
        if not obj.neighborhood:
            return None
        return obj.neighborhood.name

    def get_wijk(self, obj):
        if not obj.wijk:
            return None
        return obj.wijk.name

    class Meta:
        model = HomeownerAssociation
        fields = [
            "annotation",
            "beschermd_stadsdorpsgezicht",
            "build_year",
            "contacts",
            "district",
            "id",
            "is_priority_neighborhood",
            "is_small",
            "kvk_nummer",
            "ligt_in_beschermd_gebied",
            "monument_status",
            "name",
            "neighborhood",
            "number_of_apartments",
            "owners",
            "wijk",
            "zip_code",
        ]
        depth = 1


class HomeownerAssociationWithoutContactsSerializer(HomeownerAssociationSerializer):
    class Meta(HomeownerAssociationSerializer.Meta):
        fields = [
            field
            for field in HomeownerAssociationSerializer.Meta.fields
            if field != "contacts"
        ]


class CaseHomeownerAssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeownerAssociation
        fields = ["id", "name"]


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["fullname", "email", "phone", "role", "id"]
        depth = 1


class ContactWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True, allow_blank=False, max_length=20)
    fullname = serializers.CharField(required=True, allow_blank=False, max_length=255)
    role = serializers.CharField(required=True, allow_blank=False, max_length=255)

    class Meta:
        model = Contact
        fields = ["id", "fullname", "email", "phone", "role"]


class HomeownerAssociationSearchSerializer(serializers.Serializer):
    brkVveStatutaireNaam = serializers.CharField()
    votIdentificatie = serializers.CharField()


class HomeownerAssociationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeownerAssociation
        fields = ["annotation"]


class ApartmentSerializer(serializers.Serializer):
    straatnaam = serializers.CharField(allow_null=True, required=False)
    huisnummer = serializers.IntegerField(allow_null=True, required=False)
    huisletter = serializers.CharField(allow_null=True, required=False)
    huisnummertoevoeging = serializers.CharField(allow_null=True, required=False)
    postcode = serializers.CharField(allow_null=True, required=False)
    woonplaats = serializers.CharField(allow_null=True, required=False)
    adresseerbaarobject_id = serializers.CharField(allow_null=True, required=False)
    nummeraanduiding_id = serializers.CharField(allow_null=True, required=False)
    eigenaar_type = serializers.CharField(allow_null=True, required=False)
    eigenaar_naam = serializers.CharField(allow_null=True, required=False)
