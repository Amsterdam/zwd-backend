from rest_framework import viewsets, mixins
from .models import HomeownerAssociation
from .serializers import HomeownerAssociationSerializer


class HomeOwnerAssociationView(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = HomeownerAssociation.objects.all()
    serializer_class = HomeownerAssociationSerializer
