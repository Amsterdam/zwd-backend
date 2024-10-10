from apps import address
from apps.address.serializers import addressSerializer
from apps.homeownerassociation.mixins import HomeownerAssociationMixin
from rest_framework import viewsets


class AddressViewset(
    viewsets.ViewSet,
    HomeownerAssociationMixin,
):
    serializer_class = addressSerializer
    model = address
