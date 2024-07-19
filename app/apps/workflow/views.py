from argparse import Action
from .serializers import  CaseWorkflowSerializer
from .models import CaseWorkflow
from rest_framework import viewsets


class CaseWorkflowViewset(viewsets.ModelViewSet):
    queryset = CaseWorkflow.objects.all()
    serializer_class = CaseWorkflowSerializer
