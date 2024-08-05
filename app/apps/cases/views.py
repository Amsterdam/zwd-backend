from apps.workflow.models import CaseWorkflow
from apps.workflow.serializers import CaseWorkflowSerializer
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Case
from .serializers import CaseCreateSerializer, CaseSerializer


class CaseViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return CaseCreateSerializer
        return CaseSerializer

    @action(detail=True, methods=["get"], url_path="workflows")
    def get_workflows(self, request, pk=None):
        case = self.get_object()
        workflows = CaseWorkflow.objects.filter(case=case)
        serializer = CaseWorkflowSerializer(workflows, many=True)
        return Response(serializer.data)
