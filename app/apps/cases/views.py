from .serializers import CaseSerializer
from .models import Case
from rest_framework import viewsets


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer