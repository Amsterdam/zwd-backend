from rest_framework import serializers

from apps.workflow.models import CaseWorkflow

class CaseWorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseWorkflow
        fields = (
            "id",
            "case",
            "workflow_type",
            "workflow_version",  
            "workflow_theme_name",
            "workflow_message_name"
        )
