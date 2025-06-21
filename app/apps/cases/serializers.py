from apps.workflow.models import WorkflowOption
from apps.homeownerassociation.serializers import (
    ContactSerializer,
    CaseHomeownerAssociationSerializer,
)
from apps.cases.models import (
    ActivationTeam,
    ApplicationType,
    Case,
    CaseDocument,
    CaseStatus,
)
from apps.workflow.serializers import CaseWorkflowSerializer
from rest_framework import serializers
import magic
import os


class ActivationTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivationTeam
        fields = ("type", "subject", "meeting_date")


class CaseSerializer(serializers.ModelSerializer):
    workflows = CaseWorkflowSerializer(many=True)
    homeowner_association = CaseHomeownerAssociationSerializer()
    status = serializers.SerializerMethodField()
    activation_team = ActivationTeamSerializer(required=False)

    class Meta:
        model = Case
        fields = (
            "activation_team",
            "advice_type",
            "application_type",
            "created",
            "description",
            "end_date",
            "homeowner_association",
            "id",
            "legacy_id",
            "prefixed_dossier_id",
            "status",
            "workflows",
        )

    def get_status(self, obj):
        return obj.status.name if obj.status else None


class CaseCreateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    contacts = ContactSerializer(many=True, required=False)
    activation_team = ActivationTeamSerializer(required=False)

    class Meta:
        model = Case
        fields = (
            "advice_type",
            "application_type",
            "author",
            "contacts",
            "description",
            "homeowner_association",
            "id",
            "legacy_id",
            "activation_team",
        )

    def validate(self, data):
        # advice_type is required when application_type is ADVICE
        if data.get(
            "application_type"
        ) == ApplicationType.ADVICE.value and not data.get("advice_type"):
            raise serializers.ValidationError(
                {
                    "advice_type": "This field is required when application_type is set to ADVICE."
                }
            )
        return data


class CaseListSerializer(serializers.ModelSerializer):
    homeowner_association = CaseHomeownerAssociationSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = (
            "created",
            "end_date",
            "homeowner_association",
            "id",
            "legacy_id",
            "prefixed_dossier_id",
            "status",
            "updated",
        )

    def get_status(self, obj):
        return obj.status.name if obj.status else None


class CaseDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseDocument
        fields = ("id", "case", "document", "name", "created")

    def validate_document(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in [
            ".csv",
            ".doc",
            ".docx",
            ".jpeg",
            ".jpg",
            ".msg",
            ".pdf",
            ".png",
            ".txt",
            ".xls",
            ".xlsx",
        ]:
            raise serializers.ValidationError("File extension not allowed")

        mime = magic.Magic(mime=True)
        file_mime_type = mime.from_buffer(value.read(2048))
        value.seek(0)
        if file_mime_type not in [
            "application/CDFV2",
            "application/csv",
            "application/msoutlook",
            "application/pdf",
            "application/vnd.ms-outlook",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg",
            "image/png",
            "text/plain",
        ]:
            raise serializers.ValidationError("File type not allowed")

        return value


class CaseDocumentWithTaskSerializer(CaseDocumentSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    case_user_task_id = serializers.CharField(
        required=False, allow_null=True, write_only=True
    )

    class Meta(CaseDocumentSerializer.Meta):
        fields = CaseDocumentSerializer.Meta.fields + (
            "author",
            "case_user_task_id",
        )


class StartWorkflowSerializer(serializers.Serializer):
    workflow_option_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkflowOption.objects.all()
    )


class CaseDocumentNameUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseDocument
        fields = ["name"]


class CaseStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseStatus
        fields = ["name"]
