from argparse import Action
from .serializers import  CaseWorkflowSerializer
from .models import CaseWorkflow
from rest_framework import viewsets


class CaseWorkflowViewset(viewsets.ModelViewSet):
    queryset = CaseWorkflow.objects.all()
    serializer_class = CaseWorkflowSerializer

    def list(self, request, *args, **kwargs):
        instance = self.queryset.first()
        if instance:
            result = instance.get_workflow_spec("visit")
            print(f"Workflow Spec Result: {result}")
        return super().list(request, *args, **kwargs)
