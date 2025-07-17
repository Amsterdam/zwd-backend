from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets

from apps.cases.models import Case
from apps.homeownerassociation.models import HomeownerAssociation
from apps.address.serializers import StatusSerializer, AddressSerializer
from apps.homeownerassociation.mixins import HomeownerAssociationMixin


class AddressViewSet(
    viewsets.ViewSet,
    HomeownerAssociationMixin,
):
    serializer_class = AddressSerializer

    @action(
        detail=True,
        methods=["get"],
        url_path="status",
        serializer_class=StatusSerializer,
    )
    def get_status(self, request, pk=None):
        """
        Retrieve the Homeowner Association (vve) and related case information for a given BAG ID.
        It returns the status of the most recent case if applicable.
        This endpoint is specifically intended for use by the "Mijn Amsterdam" platform.
        """
        hoa_instance = HomeownerAssociation()
        hoa = hoa_instance.get_or_create_hoa_by_bag_id(pk)
        case = Case.objects.filter(homeowner_association=hoa).first()

        return Response(
            {
                "bag_id": pk,
                "vve_statutaire_naam": hoa.name,
                "zwd_zaak_id": case.prefixed_dossier_id if case else None,
                "zwd_zaak_status": case.status.name if case else None,
            }
        )
