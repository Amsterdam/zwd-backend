from rest_framework import serializers

from apps.workflow.serializers import CaseWorkflowSerializer
from apps.cases.models import Case

class CaseSerializer(serializers.ModelSerializer):
    workflows = CaseWorkflowSerializer(many=True)
    class Meta:
        model = Case
        fields = (
            "id",
            "description",
            "workflows"
        )
class CaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ("description", "id")
