from rest_framework import viewsets, mixins
from .models import District, HomeownerAssociation, Neighborhood, Wijk
from .serializers import (
    DistrictSerializer,
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


class HomeOwnerAssociationView(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = HomeownerAssociation.objects.all()
    serializer_class = HomeownerAssociationSerializer

    def get_serializer_class(self):
        if self.action == "cases":
            return CaseListSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["get"])
    def cases(self, request, pk=None):
        hoa = self.get_object()
        cases = Case.objects.filter(homeowner_association=hoa)
        serializer = CaseListSerializer(cases, many=True)
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


class DistrictViewset(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer

    def list(self, _, *args, **kwargs):
        names = self.get_queryset().values_list("name", flat=True).distinct()
        return Response(list(names))


class WijkViewset(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = Wijk.objects.all()
    serializer_class = WijkSerializer

    def list(self, _, *args, **kwargs):
        names = self.get_queryset().values_list("name", flat=True).distinct()
        return Response(list(names))


class NeighborhoodViewset(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = Neighborhood.objects.all()
    serializer_class = NeighborhoodSerializer

    def list(self, _, *args, **kwargs):
        names = self.get_queryset().values_list("name", flat=True).distinct()
        return Response(list(names))
