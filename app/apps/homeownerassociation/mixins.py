from rest_framework.decorators import action
from rest_framework.response import Response
from apps.homeownerassociation.models import HomeownerAssociation
from apps.homeownerassociation.serializers import HomeownerAssociationSerializer


class HomeownerAssociationMixin:
    @action(
        detail=True,
        methods=["get"],
        url_path="homeowner-association",
        serializer_class=HomeownerAssociationSerializer,
    )
    def get_by_bag_id(self, request, pk=None):
        model = HomeownerAssociation.get_or_create_hoa_by_bag_id(pk)
        serializer = HomeownerAssociationSerializer(model)
        return Response(serializer.data)
