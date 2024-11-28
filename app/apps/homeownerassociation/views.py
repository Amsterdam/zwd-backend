from rest_framework import viewsets, mixins
from .models import HomeownerAssociation
from .serializers import HomeownerAssociationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.cases.models import Case
from apps.cases.serializers import CaseListSerializer


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
        print(hoa.has_major_shareholder)
        cases = Case.objects.filter(homeowner_association=hoa)
        serializer = CaseListSerializer(cases, many=True)
        return Response(serializer.data)
