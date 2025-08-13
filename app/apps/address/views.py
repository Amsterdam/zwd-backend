from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets

from apps.cases.models import Case
from apps.homeownerassociation.models import HomeownerAssociation
from apps.address.serializers import (
    AddressSerializer,
    MijnAmsterdamSerializer,
)
from apps.homeownerassociation.mixins import HomeownerAssociationMixin


class AddressViewSet(
    viewsets.ViewSet,
    HomeownerAssociationMixin,
):
    serializer_class = AddressSerializer

    @action(
        detail=True,
        methods=["get"],
        url_path="mijn-amsterdam",
        serializer_class=MijnAmsterdamSerializer,
    )
    def get_mijn_amsterdam(self, request, pk=None):
        """
        Retrieve the address details, Homeowner Association (vve) and related cases for a given BAG ID.
        This endpoint is specifically intended for use by the "Mijn Amsterdam" platform.
        """
        hoa_instance = HomeownerAssociation()
        hoa = hoa_instance.get_or_create_hoa_by_bag_id(pk)

        response_data = {
            "bag_id": pk,
            "beschermd_stadsdorpsgezicht": hoa.beschermd_stadsdorpsgezicht,
            "build_year": hoa.build_year,
            "district": hoa.district.name if hoa.district else None,
            "kvk_nummer": hoa.kvk_nummer,
            "ligt_in_beschermd_gebied": hoa.ligt_in_beschermd_gebied,
            "monument_status": hoa.monument_status,
            "name": hoa.name,
            "neighborhood": hoa.neighborhood.name if hoa.neighborhood else None,
            "number_of_apartments": hoa.number_of_apartments,
            "wijk": hoa.wijk.name if hoa.wijk else None,
            "zip_code": hoa.zip_code,
            "cases": Case.objects.filter(homeowner_association=hoa),
        }

        serializer = MijnAmsterdamSerializer(response_data)
        return Response(serializer.data)
