from apps.address.models import Address
from apps.cases.serializers import MijnAmsterdamCaseListSerializer
from rest_framework import serializers


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class MijnAmsterdamSerializer(serializers.Serializer):
    bag_id = serializers.CharField()
    beschermd_stadsdorpsgezicht = serializers.CharField(allow_null=True, required=False)
    build_year = serializers.IntegerField()
    district = serializers.CharField(allow_null=True, required=False)
    kvk_nummer = serializers.CharField(allow_null=True, required=False)
    ligt_in_beschermd_gebied = serializers.CharField(allow_null=True, required=False)
    monument_status = serializers.CharField(allow_null=True, required=False)
    name = serializers.CharField()
    neighborhood = serializers.CharField(allow_null=True, required=False)
    number_of_apartments = serializers.IntegerField()
    wijk = serializers.CharField(allow_null=True, required=False)
    zip_code = serializers.CharField(allow_null=True, required=False)
    cases = MijnAmsterdamCaseListSerializer(many=True)
