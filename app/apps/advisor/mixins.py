from apps.advisor.models import Advisor
from apps.advisor.serializers import CaseAdvisorSerializer
from rest_framework.decorators import action
from apps.cases.models import AdviceType, Case
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.db.models import Q


class CaseAdvisorMixin:
    @extend_schema(
        responses=CaseAdvisorSerializer(many=True),
        description="Update the advisor for a case",
    )
    @action(
        detail=True,
        methods=["get"],
        serializer_class=CaseAdvisorSerializer,
        pagination_class=None,
    )
    def advisors(self, _, pk):
        try:
            case = Case.objects.get(pk=pk)
        except Case.DoesNotExist:
            return Response(
                {"error": "Case not found"}, status=status.HTTP_404_NOT_FOUND
            )
        query = Q()
        if case.advice_type == AdviceType.HBO.value:
            query = Q(advice_type_hbo=True, enabled=True)
        if case.advice_type == AdviceType.ENERGY_ADVICE.value:
            query = Q(advice_type_energieadvies=True, enabled=True)
        if case.homeowner_association.is_small:
            query = Q(small_hoa=True, enabled=True)
        advisors = Advisor.objects.filter(query).distinct().order_by("name")

        serialized_advisors = CaseAdvisorSerializer(advisors, many=True)
        return Response(serialized_advisors.data)
