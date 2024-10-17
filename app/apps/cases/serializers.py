from apps.homeownerassociation.serializers import ContactSerializer
from apps.cases.models import Case
from apps.workflow.serializers import CaseWorkflowSerializer
from rest_framework import serializers


class CaseSerializer(serializers.ModelSerializer):
    workflows = CaseWorkflowSerializer(many=True)
    homeowner_association = serializers.SerializerMethodField()

    def get_homeowner_association(self, obj):
        if not obj.homeowner_association:
            return None
        return obj.homeowner_association.name

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
    contacts = ContactSerializer(many=True, required=False)

    class Meta:
        model = Case
        fields = (
            "id",
            "description",
            "advice_type",
            "homeowner_association",
            "contacts",
        )
