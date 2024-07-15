from rest_framework import serializers

from apps.workflow.models import CaseWorkflow

class CaseWorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseWorkflow
        fields = (
            "id",
            "case"
        )
