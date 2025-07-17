from apps.address.models import Address
from rest_framework import serializers


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class StatusSerializer(serializers.Serializer):
    bag_id = serializers.CharField()
    vve_statutaire_naam = serializers.CharField()
    zwd_zaak_id = serializers.CharField()
    zwd_zaak_status = serializers.CharField()
