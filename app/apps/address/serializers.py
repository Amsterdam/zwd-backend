from apps.address.models import Address
from apps.cases.serializers import EXTENSION_TO_MIME, MijnAmsterdamCaseListSerializer
from rest_framework import serializers
import base64
import binascii
import magic


MIME_TYPE_TO_EXTENSION = {
    mime_type: extension
    for extension, mime_types in EXTENSION_TO_MIME.items()
    for mime_type in mime_types
}


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class MijnAmsterdamSerializer(serializers.Serializer):
    bag_id = serializers.CharField()
    beschermd_stadsdorpsgezicht = serializers.CharField(allow_null=True, required=False)
    build_year = serializers.IntegerField()
    district = serializers.CharField(allow_null=True, required=False)
    kvk_nummer = serializers.CharField(allow_null=True, required=False)
    ligt_in_beschermd_gebied = serializers.CharField(allow_null=True, required=False)
    monument_status = serializers.CharField(allow_null=True, required=False)
    name = serializers.CharField()
    neighborhood = serializers.CharField(allow_null=True, required=False)
    number_of_apartments = serializers.IntegerField()
    wijk = serializers.CharField(allow_null=True, required=False)
    zip_code = serializers.CharField(allow_null=True, required=False)
    cases = MijnAmsterdamCaseListSerializer(many=True)
    is_priority_neighborhood = serializers.BooleanField()
    has_advice_case = serializers.BooleanField()
    homeowner_association_id = serializers.IntegerField()
    has_major_shareholder = serializers.BooleanField()


class MijnAmsterdamEindpresentatieSerializer(serializers.Serializer):
    case_id = serializers.IntegerField()
    eindpresentatie_document_id = serializers.IntegerField(allow_null=True)


class DuurzaamWonenDocumentUploadSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_base64 = serializers.CharField()
    name = serializers.CharField(max_length=100, required=False)

    def validate_file_base64(self, value):
        encoded_value = value.strip()

        if encoded_value.startswith("data:") and "," in encoded_value:
            encoded_value = encoded_value.split(",", 1)[1]

        try:
            decoded_file = base64.b64decode(encoded_value, validate=True)
        except (ValueError, binascii.Error):
            raise serializers.ValidationError("Invalid base64 file content.")

        if not decoded_file:
            raise serializers.ValidationError("Uploaded file cannot be empty.")

        return decoded_file

    def validate(self, attrs):
        file_base64_value = self.initial_data.get("file_base64", "")
        if not isinstance(file_base64_value, str):
            file_base64_value = str(file_base64_value or "")
        file_base64_value = file_base64_value.strip()
        detected_extension = None

        if file_base64_value.startswith("data:") and "," in file_base64_value:
            metadata = file_base64_value.split(",", 1)[0]
            mime_type = metadata[5:].split(";", 1)[0].lower()
            detected_extension = MIME_TYPE_TO_EXTENSION.get(mime_type)

        # Fallback for plain base64 payloads without data URL metadata.
        if not detected_extension:
            decoded_file = attrs.get("file_base64")
            if decoded_file:
                detected_mime_type = magic.Magic(mime=True).from_buffer(
                    decoded_file[:2048]
                )
                detected_extension = MIME_TYPE_TO_EXTENSION.get(detected_mime_type)

        attrs["detected_extension"] = detected_extension
        return attrs
