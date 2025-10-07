from rest_framework import viewsets, mixins

from clients.dso_client import DsoClient
from .models import (
    District,
    HomeownerAssociationCommunicationNote,
    HomeownerAssociation,
    Neighborhood,
    Wijk,
)
from .serializers import (
    ApartmentSerializer,
    DistrictSerializer,
    HomeownerAssociationCommunicationNoteCreateSerializer,
    HomeownerAssociationCommunicationNoteSerializer,
    HomeownerAssociationCommunicationNoteUpdateSerializer,
    HomeownerAssociationUpdateSerializer,
    HomeownerAssociationSearchSerializer,
    HomeownerAssociationSerializer,
    NeighborhoodSerializer,
    WijkSerializer,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.cases.models import Case
from apps.cases.serializers import CaseListSerializer
from rest_framework import status
from apps.homeownerassociation.models import PriorityZipCode
from .mixins import ContactMixin
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema


class HomeOwnerAssociationView(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    ContactMixin,
):
    queryset = HomeownerAssociation.objects.all()
    serializer_class = HomeownerAssociationSerializer

    def get_serializer_class(self):
        if self.action == "cases":
            return CaseListSerializer
        if self.action == "apartments":
            return ApartmentSerializer
        if self.action in ["update", "partial_update"]:
            return HomeownerAssociationUpdateSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["get"])
    def cases(self, request, pk=None):
        hoa = self.get_object()
        cases = Case.objects.filter(homeowner_association=hoa)
        serializer = CaseListSerializer(cases, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def apartments(self, request, pk=None):
        hoa = self.get_object()
        dso_client = DsoClient()
        apartments = dso_client.get_hoa_by_name(hoa.name)
        data_filtered = [
            {
                "straatnaam": a.get("adres"),
                "huisnummer": a.get("huisnummer"),
                "huisletter": a.get("huisletter"),
                "huisnummertoevoeging": a.get("huisnummertoevoeging"),
                "postcode": a.get("postcode"),
                "woonplaats": a.get("woonplaats"),
                "adresseerbaarobject_id": a.get("votIdentificatie"),
                "nummeraanduiding_id": a.get("bagNagId"),
                "eigenaar_type": a.get("eigCategorieEigenaar"),
                "eigenaar_naam": a.get("brkStatutaireNaam"),
            }
            for a in apartments
        ]
        serializer = ApartmentSerializer(data_filtered, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        url_path="priority-zipcode",
        methods=["post"],
    )
    def create_priority_zip_code(self, request):
        request_data = request.data
        zip_code = request_data.get("zip_code")
        if not zip_code:
            return Response(
                {"detail": "Zip code is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        PriorityZipCode.objects.get_or_create(zip_code=zip_code)
        return Response(
            {"message": f"Zip code {zip_code} has been added to priority zip codes"},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        methods=["get"],
        responses={200: HomeownerAssociationCommunicationNoteSerializer(many=True)},
        description="List communication notes for a homeowner association",
    )
    @extend_schema(
        methods=["post"],
        request=HomeownerAssociationCommunicationNoteCreateSerializer,
        responses={201: HomeownerAssociationCommunicationNoteSerializer},
        description="Create a communication note for a homeowner association",
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="communication-notes",
        filter_backends=[],
        pagination_class=None,
    )
    def communication_notes(self, request, pk=None):
        hoa = self.get_object()

        if request.method == "GET":
            notes = HomeownerAssociationCommunicationNote.objects.filter(
                homeowner_association=hoa
            ).order_by("-date")
            serializer = HomeownerAssociationCommunicationNoteSerializer(
                notes, many=True
            )
            return Response(serializer.data)

        serializer = HomeownerAssociationCommunicationNoteCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        note = HomeownerAssociationCommunicationNote.objects.create(
            homeowner_association=hoa, **serializer.validated_data
        )
        return Response(
            HomeownerAssociationCommunicationNoteSerializer(note).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        methods=["patch"],
        request=HomeownerAssociationCommunicationNoteUpdateSerializer,
        responses={200: HomeownerAssociationCommunicationNoteSerializer},
        description="Update a communication note",
    )
    @extend_schema(
        methods=["delete"],
        responses={204: None},
        description="Delete a communication note",
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="communication-notes/(?P<note_id>[^/.]+)",
    )
    def communication_note_detail(self, request, pk=None, note_id=None):
        hoa = self.get_object()
        note = get_object_or_404(
            HomeownerAssociationCommunicationNote, homeowner_association=hoa, id=note_id
        )

        if request.method == "PATCH":
            serializer = HomeownerAssociationCommunicationNoteUpdateSerializer(
                note, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(HomeownerAssociationCommunicationNoteSerializer(note).data)

        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        url_path="search",
        methods=["get"],
    )
    def search_hoa_by_name(self, request):
        hoa_name = request.query_params.get("hoa_name")
        if not hoa_name:
            return Response(
                {"detail": "Homeowner Association name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dso_client = DsoClient()
        result = dso_client.search_hoa_by_name(hoa_name)
        serializer = HomeownerAssociationSearchSerializer(result, many=True)
        return Response(serializer.data)


class DistrictViewset(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer

    def get_case_filtered_queryset(self):
        return District.objects.filter(homeowner_associations__cases__isnull=False)

    def list(self, _, *args, **kwargs):
        names = (
            self.get_case_filtered_queryset().values_list("name", flat=True).distinct()
        )
        return Response(list(names))


class WijkViewset(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = Wijk.objects.all()
    serializer_class = WijkSerializer

    def get_case_filtered_queryset(self):
        return Wijk.objects.filter(homeowner_associations__cases__isnull=False)

    def list(self, _, *args, **kwargs):
        names = (
            self.get_case_filtered_queryset().values_list("name", flat=True).distinct()
        )
        return Response(list(names))


class NeighborhoodViewset(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = Neighborhood.objects.all()
    serializer_class = NeighborhoodSerializer

    def get_case_filtered_queryset(self):
        return Neighborhood.objects.filter(homeowner_associations__cases__isnull=False)

    def list(self, _, *args, **kwargs):
        names = (
            self.get_case_filtered_queryset().values_list("name", flat=True).distinct()
        )
        return Response(list(names))
