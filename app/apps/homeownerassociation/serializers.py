from apps.homeownerassociation.models import HomeownerAssociation
from rest_framework import serializers


class HomeownerAssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeownerAssociation
        fields = [
            "name",
            "build_year",
            "number_of_appartments",
        ]
