from apps.homeownerassociation.serializers import ContactSerializer
from apps.cases.models import Case
from apps.cases.models import Case, CaseDocument
from apps.workflow.serializers import CaseWorkflowSerializer
from rest_framework import serializers
import magic
import os


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


class CaseListSerializer(serializers.ModelSerializer):
    homeowner_association = serializers.SerializerMethodField()

    def get_homeowner_association(self, obj):
        if not obj.homeowner_association:
            return None
        return obj.homeowner_association.name

    class Meta:
        model = Case
        fields = ("id", "homeowner_association", "created")


class CaseDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseDocument
        fields = ("id", "case", "document", "name", "created")

    def validate_document(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in [".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"]:
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
        ]:
            raise serializers.ValidationError("File type not allowed")

        return value
