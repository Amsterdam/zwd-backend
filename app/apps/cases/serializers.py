import logging
from apps.workflow.models import WorkflowOption
from apps.homeownerassociation.serializers import (
    ContactSerializer,
    CaseHomeownerAssociationSerializer,
)
from apps.cases.models import (
    ActivationTeam,
    ApplicationType,
    Case,
    CaseClose,
    CaseCloseReason,
    CaseDocument,
    CaseStatus,
)
from apps.workflow.serializers import CaseWorkflowSerializer
from rest_framework import serializers
import magic
import os

logger = logging.getLogger(__name__)


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


class MijnAmsterdamCaseListSerializer(serializers.ModelSerializer):
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


EXTENSION_TO_MIME = {
    ".pdf": ["application/pdf"],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
    ".doc": ["application/msword"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    ".xls": ["application/vnd.ms-excel"],
    ".txt": ["text/plain"],
    ".csv": ["text/csv", "text/plain", "application/csv"],
    ".png": ["image/png"],
    ".jpeg": ["image/jpeg"],
    ".jpg": ["image/jpeg"],
    ".msg": ["application/vnd.ms-outlook", "application/msoutlook"],
}

# File types that do NOT have magic bytes and should be skipped in magic byte validation
# .msg has old Microsoft Outlook format with specific magic bytes and a newer format without magic bytes
MAGIC_BYTES_EXCEPTIONS = [".csv", ".txt", ".msg"]

# Magic byte patterns per file type
MAGIC_BYTES = {
    b"%PDF-": [".pdf"],
    b"\x50\x4B\x03\x04": [".docx", ".xlsx", ".zip"],
    b"\xD0\xCF\x11\xE0": [".doc", ".xls", ".msg"],
    b"\x89PNG\r\n\x1a\n": [".png"],
    b"\xFF\xD8\xFF": [".jpeg", ".jpg"],
}


def detect_magic_extension(file_header: bytes):
    return next(
        (exts for magic, exts in MAGIC_BYTES.items() if file_header.startswith(magic)),
        None,
    )


class CaseDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseDocument
        fields = ("id", "case", "document", "name", "created")

    def validate_document(self, value):
        # Validatefile extension
        try:
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in EXTENSION_TO_MIME:
                raise serializers.ValidationError("File extension not allowed")

            # Detect real MIME type
            mime = magic.Magic(mime=True)
            file_mime_type = mime.from_buffer(value.read(2048))
            value.seek(0)

            allowed_mimes = EXTENSION_TO_MIME.get(ext)
            if file_mime_type not in allowed_mimes:
                raise serializers.ValidationError(
                    "MIME-type does not match file extension"
                )

            # Check magic bytes
            header = value.read(16)
            value.seek(0)

            magic_exts = detect_magic_extension(header)
            logger.error(f"-------- >>> magic_exts: {magic_exts}, ext: {ext}")
        except Exception as e:
            print("-------- >>> File validation error:", str(e))
            logger.error(f"File validation error: {str(e)}")
            raise serializers.ValidationError(f"File validation error: {str(e)}")
        if magic_exts is None:
            if ext in MAGIC_BYTES_EXCEPTIONS:
                return value
            raise serializers.ValidationError(
                "File type could not be verified based on magic bytes"
            )

        if ext not in magic_exts:
            raise serializers.ValidationError(
                "Magic bytes do not match the file extension"
            )

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


class CaseCloseReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseCloseReason
        fields = "__all__"


class CaseCloseSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CaseClose
        fields = "__all__"

    def validate_case(self, value):
        """
        Validate if there is no existing CaseClose for the given case.
        """
        if CaseClose.objects.filter(case=value).exists():
            raise serializers.ValidationError(
                f"A CaseClose already exists for Case {value.id}."
            )
        return value
