
from rest_framework.response import Response
from apps.workflow.serializers import CaseUserTaskSerializer, CaseWorkflowSerializer
from apps.workflow.models import CaseUserTask, CaseWorkflow
from .serializers import CaseCreateSerializer, CaseSerializer
from .models import Case
from rest_framework import viewsets, mixins
from rest_framework.decorators import action

class CaseViewSet(viewsets.ModelViewSet, mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    def get_serializer_class(self):
        if self.action == 'create':
            return CaseCreateSerializer
        return CaseSerializer
    
    @action(detail=True, methods=["get"], url_path="workflows")
    def get_workflows(self, request, pk=None):
        case = self.get_object()
        workflows = CaseWorkflow.objects.filter(case=case)
        serializer = CaseWorkflowSerializer(workflows, many=True)
        return Response(serializer.data)