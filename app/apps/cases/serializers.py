from apps.workflow.models import WorkflowOption
from apps.homeownerassociation.serializers import (
    ContactSerializer,
    CaseHomeownerAssociationSerializer,
)
from apps.cases.models import Case, CaseDocument, CaseStatus
from apps.workflow.serializers import CaseWorkflowSerializer
from rest_framework import serializers
import magic
import os


class CaseSerializer(serializers.ModelSerializer):
    workflows = CaseWorkflowSerializer(many=True)
    homeowner_association = CaseHomeownerAssociationSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = (
            "id",
            "created",
            "end_date",
            "description",
            "workflows",
            "advice_type",
            "homeowner_association",
            "legacy_id",
            "status",
        )

    def get_status(self, obj):
        return obj.status.name if obj.status else None


class CaseCreateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    contacts = ContactSerializer(many=True, required=False)

    class Meta:
        model = Case
        fields = (
            "id",
            "description",
            "advice_type",
            "homeowner_association",
            "contacts",
            "author",
            "legacy_id",
        )


class CaseListSerializer(serializers.ModelSerializer):
    homeowner_association = CaseHomeownerAssociationSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = (
            "id",
            "created",
            "homeowner_association",
            "legacy_id",
            "status",
            "end_date",
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
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".png",
            ".jpg",
            ".jpeg",
            ".xlsx",
            ".xls",
            ".csv",
            ".msg",
        ]:
            raise serializers.ValidationError("File extension not allowed")

        mime = magic.Magic(mime=True)
        file_mime_type = mime.from_buffer(value.read(2048))
        value.seek(0)
        if file_mime_type not in [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "image/png",
            "image/jpeg",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/csv",
            "application/CDFV2",
            "application/vnd.ms-outlook",
            "application/msoutlook",
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
            "case_user_task_id",
            "author",
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
