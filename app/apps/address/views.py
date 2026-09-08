import mimetypes
import os

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import FileResponse

from apps.cases.models import AdviceType, ApplicationType, Case
from apps.cases.models import CaseDocument
from apps.cases.serializers import CaseDocumentSerializer
from apps.homeownerassociation.models import HomeownerAssociation
from apps.workflow.models import GenericCompletedTask
from apps.address.serializers import (
    AddressSerializer,
    DuurzaamWonenDocumentUploadSerializer,
    MijnAmsterdamSerializer,
    MijnAmsterdamEindpresentatieSerializer,
)
from apps.homeownerassociation.mixins import HomeownerAssociationMixin


class AddressViewSet(
    viewsets.ViewSet,
    HomeownerAssociationMixin,
):
    serializer_class = AddressSerializer

    def _build_platform_response_data(self, bag_id):
        hoa_instance = HomeownerAssociation()
        hoa = hoa_instance.get_or_create_hoa_by_bag_id(bag_id)
        cases_qs = Case.objects.filter(homeowner_association=hoa)

        return {
            "bag_id": bag_id,
            "beschermd_stadsdorpsgezicht": hoa.beschermd_stadsdorpsgezicht,
            "build_year": hoa.build_year,
            "district": hoa.district.name if hoa.district else None,
            "kvk_nummer": hoa.kvk_nummer,
            "ligt_in_beschermd_gebied": hoa.ligt_in_beschermd_gebied,
            "monument_status": hoa.monument_status,
            "name": hoa.name,
            "homeowner_association_id": hoa.id,
            "neighborhood": hoa.neighborhood.name if hoa.neighborhood else None,
            "number_of_apartments": hoa.number_of_apartments,
            "wijk": hoa.wijk.name if hoa.wijk else None,
            "zip_code": hoa.zip_code,
            "cases": cases_qs,
            "is_priority_neighborhood": hoa.is_priority_neighborhood,
            "has_advice_case": cases_qs.filter(
                application_type=ApplicationType.ADVICE.value,
                advice_type__in=(
                    AdviceType.ENERGY_ADVICE.value,
                    AdviceType.HBO.value,
                ),
            ).exists(),
            "has_major_shareholder": hoa.has_major_shareholder,
        }

    @action(
        detail=True,
        methods=["get"],
        url_path="mijn-amsterdam",
        serializer_class=MijnAmsterdamSerializer,
    )
    def get_mijn_amsterdam(self, request, pk=None):
        """
        Retrieve the address details, Homeowner Association (vve) and related cases for a given BAG ID.
        This endpoint is specifically intended for use by the "Mijn Amsterdam" platform.
        """
        response_data = self._build_platform_response_data(pk)

        serializer = MijnAmsterdamSerializer(response_data)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        url_path="duurzaamwonen",
        serializer_class=MijnAmsterdamSerializer,
    )
    def get_duurzaamwonen(self, request, pk=None):
        """
        Retrieve the same address, Homeowner Association (vve) and case data as mijn-amsterdam.
        This endpoint is intended for use by the "Duurzaam Wonen" platform on amsterdam.nl.
        """
        response_data = self._build_platform_response_data(pk)

        serializer = MijnAmsterdamSerializer(response_data)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="mijn-amsterdam/(?P<case_id>[^/.]+)/eindpresentatie-document",
        url_name="mijn-amsterdam-eindpresentatie-document",
        serializer_class=MijnAmsterdamEindpresentatieSerializer,
    )
    def get_mijn_amsterdam_eindpresentatie_document(self, request, case_id=None):
        """
        Retrieve the document linked to the completed "Upload eindpresentatie" task for a case.
        Returns null when the task/document link is not present.
        """
        case = get_object_or_404(Case, id=case_id)
        document = self._get_eindpresentatie_document_for_case(case.id)

        serializer = MijnAmsterdamEindpresentatieSerializer(
            {
                "case_id": case.id,
                "eindpresentatie_document_id": document.id if document else None,
            }
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        url_path="duurzaamwonen/(?P<case_id>[^/.]+)/document",
        url_name="duurzaamwonen-document",
        serializer_class=DuurzaamWonenDocumentUploadSerializer,
    )
    def upload_duurzaamwonen_document(self, request, case_id=None):
        """
        Upload a document for a case from a base64-encoded payload.
        """
        case = get_object_or_404(Case, id=case_id)

        upload_serializer = DuurzaamWonenDocumentUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)

        file_name = os.path.basename(upload_serializer.validated_data["file_name"])
        if not file_name:
            file_name = "document"

        _, file_extension = os.path.splitext(file_name)
        if not file_extension:
            detected_extension = upload_serializer.validated_data.get(
                "detected_extension"
            )
            if detected_extension:
                file_name = f"{file_name}{detected_extension}"

        document_name = upload_serializer.validated_data.get("name") or file_name
        decoded_file = upload_serializer.validated_data["file_base64"]

        case_document_serializer = CaseDocumentSerializer(
            data={
                "case": case.id,
                "name": document_name,
                "document": ContentFile(decoded_file, name=file_name),
            }
        )
        case_document_serializer.is_valid(raise_exception=True)
        case_document = case_document_serializer.save()

        response_serializer = MijnAmsterdamEindpresentatieSerializer(
            {
                "case_id": case.id,
                "eindpresentatie_document_id": case_document.id,
            }
        )

        return Response(response_serializer.data, status=201)

    @action(
        detail=False,
        methods=["get"],
        url_path="mijn-amsterdam/(?P<case_id>[^/.]+)/eindpresentatie-document/download",
        url_name="mijn-amsterdam-eindpresentatie-document-download",
    )
    def download_mijn_amsterdam_eindpresentatie_document(self, request, case_id=None):
        """
        Download the document linked to the completed "Eindpresentatie" task for a case.
        """
        case = get_object_or_404(Case, id=case_id)
        case_document = self._get_eindpresentatie_document_for_case(case.id)

        if not case_document:
            return Response({"detail": "Document not found."}, status=404)

        file_name = case_document.document.name
        mime_type, _ = mimetypes.guess_type(file_name)
        content_type = mime_type or "application/octet-stream"

        with default_storage.open(file_name, "rb") as file:
            response = FileResponse(file, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'
            return response

    def _get_eindpresentatie_document_for_case(self, case_id):
        completed_task = (
            GenericCompletedTask.objects.filter(
                case_id=case_id,
                task_name="Activity_0qoynbp",
            )
            .order_by("-date_added")
            .first()
        )

        if not completed_task:
            return None

        mapped_form_data = (completed_task.variables or {}).get("mapped_form_data", {})
        document_name = (mapped_form_data.get("document_name") or {}).get("value")

        if document_name:
            return (
                CaseDocument.objects.filter(case_id=case_id, name=document_name)
                .order_by("-created")
                .first()
            )

        return CaseDocument.objects.filter(case_id=case_id).order_by("-created").first()
