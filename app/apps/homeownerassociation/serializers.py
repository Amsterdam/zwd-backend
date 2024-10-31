from apps.homeownerassociation.models import (
    Contact,
    District,
    HomeownerAssociation,
    Neighborhood,
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


class HomeownerAssociationSerializer(serializers.ModelSerializer):
    district = serializers.SerializerMethodField()
    neighborhood = serializers.SerializerMethodField()

    def get_neighborhood(self, obj):
        if not obj.neighborhood:
            return None
        return obj.neighborhood.name

    def get_district(self, obj):
        if not obj.district:
            return None
        return obj.district.name

    class Meta:
        model = HomeownerAssociation
        fields = [
            "id",
            "name",
            "build_year",
            "number_of_appartments",
            "contacts",
            "owners",
            "district",
            "neighborhood",
            "zip_code",
        ]
        depth = 1


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "fullname",
            "email",
            "phone",
            "role",
        ]
        depth = 1
