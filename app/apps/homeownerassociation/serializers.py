from apps.homeownerassociation.models import Contact, HomeownerAssociation
from rest_framework import serializers


class HomeownerAssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeownerAssociation
        fields = ["id", "name", "build_year", "number_of_appartments", "contacts"]
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
