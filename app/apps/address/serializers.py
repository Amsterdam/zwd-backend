from apps.address.models import Address
from rest_framework import serializers


class addressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
