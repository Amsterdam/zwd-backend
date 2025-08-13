from rest_framework import viewsets, mixins
from .models import Advisor
from .serializers import CaseAdvisorSerializer


class AdvisorViewset(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    queryset = Advisor.objects.filter(enabled=True).order_by("name")
    serializer_class = CaseAdvisorSerializer
    pagination_class = None
