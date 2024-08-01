from .serializers import CaseCreateSerializer, CaseSerializer
from .models import Case
from rest_framework import viewsets, mixins


class CaseViewSet(viewsets.ModelViewSet, mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    def get_serializer_class(self):
        if self.action == 'create':
            return CaseCreateSerializer
        return CaseSerializer