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
            "number_of_appartments",
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
            "number_of_appartments",
            "owners",
            "wijk",
            "zip_code",
        ]
        depth = 1


class CaseHomeownerAssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeownerAssociation
        fields = ["id", "name"]


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["fullname", "email", "phone", "role", "id"]
        depth = 1


class HomeownerAssociationSearchSerializer(serializers.Serializer):
    brkVveStatutaireNaam = serializers.CharField()
    votIdentificatie = serializers.CharField()
