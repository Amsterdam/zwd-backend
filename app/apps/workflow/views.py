from .serializers import  CaseWorkflowSerializer
from .models import CaseWorkflow
from rest_framework import viewsets


class CaseWorkflowViewset(viewsets.ModelViewSet):
    queryset = CaseWorkflow.objects.all()
    serializer_class = CaseWorkflowSerializer

    def list(self, request, *args, **kwargs):
        self.queryset.model().get_workflow_spec("summon")
        return super().list(request, *args, **kwargs)

