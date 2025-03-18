import mimetypes
from apps.advisor.serializers import UpdateCaseAdvisorSerializer
from apps.homeownerassociation.models import Contact
from apps.events.serializers import CaseEventSerializer
from apps.events.mixins import CaseEventsMixin
from apps.advisor.mixins import CaseAdvisorMixin
from apps.workflow.models import CaseWorkflow, WorkflowOption
from apps.workflow.serializers import CaseWorkflowSerializer, WorkflowOptionSerializer
from rest_framework import mixins, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Case, CaseDocument
from .serializers import (
    CaseCreateSerializer,
    CaseDocumentSerializer,
    CaseSerializer,
    CaseListSerializer,
    StartWorkflowSerializer,
)
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.http import FileResponse
from apps.workflow.tasks import task_create_main_worflow_for_case
from apps.workflow.tasks import task_start_worflow
from apps.advisor.models import Advisor
from utils.pagination import CustomPagination


class CaseViewSet(
    CaseEventsMixin,
    CaseAdvisorMixin,
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = Case.objects.all().prefetch_related("homeowner_association")
    serializer_class = CaseSerializer
    pagination_class = CustomPagination
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ["id", "created"]

    def get_serializer_class(self):
        if self.action == "create_document" or self.action == "get_documents":
            return CaseDocumentSerializer
        elif self.action == "create":
            return CaseCreateSerializer
        elif self.action == "list":
            return CaseListSerializer
        elif self.action == "events":
            return CaseEventSerializer

        return CaseSerializer

    @action(detail=True, methods=["get"], url_path="workflows")
    def get_workflows(self, request, pk=None):
        case = self.get_object()
        workflows = CaseWorkflow.objects.filter(case=case, completed=False)
        serializer = CaseWorkflowSerializer(workflows, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = CaseCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        # Prevents exception on case creation
        contacts_data = validated_data.pop("contacts", [])
        case = Case.objects.create(**validated_data)
        Contact.process_contacts(case, contacts_data)
        self.start_workflow(case, request.user.id)
        return Response(CaseSerializer(case).data, status=201)

    def start_workflow(self, case, user_id):
        task = task_create_main_worflow_for_case.delay(
            case_id=case.id, data={"initiated_by": user_id}
        )
        task.wait(timeout=None, interval=0.5)
        start_workflow_task = task_start_worflow.delay(
            CaseWorkflow.objects.get(case=case).id
        )
        start_workflow_task.wait(timeout=None, interval=0.5)

    @action(
        detail=False, methods=["post"], url_path="documents", name="cases-documents"
    )
    def create_document(self, request):
        serializer = CaseDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="documents")
    def get_documents(self, request, pk=None):
        case = self.get_object()
        serializer = CaseDocumentSerializer(case.documents, many=True)
        return Response(serializer.data)

    @action(
        detail=True, methods=["get"], url_path="documents/download/(?P<doc_id>[^/.]+)"
    )
    def download_document(self, request, pk=None, doc_id=None):
        case = self.get_object()
        case_document = get_object_or_404(CaseDocument, case=case, id=doc_id)
        file_name = case_document.document.name
        # Add the mime type so the frontend knows how to handle the file.
        mime_type, _ = mimetypes.guess_type(file_name)
        content_type = mime_type or "application/octet-stream"

        with default_storage.open(file_name, "rb") as file:
            response = FileResponse(file, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'
            return response

    @action(detail=True, methods=["delete"], url_path="documents/(?P<doc_id>[^/.]+)")
    def delete_document(self, request, pk=None, doc_id=None):
        case = self.get_object()
        case_document = get_object_or_404(CaseDocument, case=case, id=doc_id)
        case_document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        responses=StartWorkflowSerializer,
        description="Start subworkflow",
    )
    @action(
        detail=True,
        url_path="processes/start",
        methods=["post"],
        serializer_class=StartWorkflowSerializer,
    )
    def start_process(self, request, pk):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            case = self.get_object()
            instance = data["workflow_option_id"]

            workflow_type = "sub_workflow"
            case_workflow = CaseWorkflow.objects.create(
                case=case,
                workflow_type=workflow_type,
                workflow_message_name=instance.message_name,
                data={"initiated_by": request.user.id},
            )
            task = task_start_worflow.delay(case_workflow.id)
            task.wait(timeout=None, interval=0.5)
            return Response(
                data=f"Workflow has started {str(instance)}",
                status=status.HTTP_200_OK,
            )

        return Response(
            data="Workflow has not started. serializer not valid",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @extend_schema(
        responses=WorkflowOptionSerializer(many=True),
        description="Retrieve workflow options",
    )
    @action(
        detail=False,
        url_path="processes",
        url_name="processes",
        methods=["get"],
        serializer_class=WorkflowOptionSerializer,
        pagination_class=None,
    )
    def get_workflow_options(self, request):
        serializer = WorkflowOptionSerializer(
            WorkflowOption.objects.all(),
            many=True,
        )
        return Response(serializer.data)

    @extend_schema(
        request=UpdateCaseAdvisorSerializer,
        responses={200: OpenApiTypes.STR},
        description="Update the advisor for a case",
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="advisor",
        serializer_class=UpdateCaseAdvisorSerializer,
    )
    def update_advisor(self, request, pk=None):
        case = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            advisor_id = request.data.get("advisor")
            advisor = get_object_or_404(Advisor, pk=advisor_id)
            case.advisor = advisor
            case.save()
            return Response("Case updated", status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses=CaseListSerializer,
        description="Retrieve case by legacy id",
    )
    @action(
        detail=False,
        url_path="legacy/(?P<id>[^/.]+)",
        url_name="legacy",
        methods=["get"],
        serializer_class=CaseListSerializer,
    )
    def get_case_id_by_legacy_Id(self, _, id):
        case = Case.objects.filter(legacy_id=id).first()
        if case is None:
            return Response(
                data="Case not found",
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(case.id)
