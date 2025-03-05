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
    wijk = serializers.SerializerMethodField()
    is_small = serializers.BooleanField()

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
            "id",
            "name",
            "build_year",
            "number_of_appartments",
            "contacts",
            "owners",
            "district",
            "neighborhood",
            "wijk",
            "zip_code",
            "is_small",
            "monument_status",
            "ligt_in_beschermd_gebied",
            "beschermd_stadsdorpsgezicht",
            "is_priority_neighborhood",
        ]
        depth = 1


class CaseHomeownerAssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeownerAssociation
        fields = ["id", "name"]


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
