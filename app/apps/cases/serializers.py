from apps.cases.models import Case
from apps.workflow.serializers import CaseWorkflowSerializer
from rest_framework import serializers


class CaseSerializer(serializers.ModelSerializer):
    workflows = CaseWorkflowSerializer(many=True)

    class Meta:
        model = Case
        fields = (
            "id",
            "description",
            "workflows",
            "advice_type",
            "homeowner_association",
        )


class CaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ("id", "description", "advice_type", "homeowner_association")
