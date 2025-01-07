import mimetypes
from apps.homeownerassociation.models import Contact
from apps.events.serializers import CaseEventSerializer
from apps.events.mixins import CaseEventsMixin
from apps.workflow.models import CaseWorkflow, WorkflowOption
from apps.workflow.serializers import CaseWorkflowSerializer, WorkflowOptionSerializer
from rest_framework import mixins, viewsets
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
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.http import FileResponse
from apps.workflow.tasks import task_create_main_worflow_for_case
from apps.workflow.tasks import task_start_worflow


class CaseViewSet(
    CaseEventsMixin,
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = Case.objects.all().prefetch_related("homeowner_association")
    serializer_class = CaseSerializer

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
        serializer = CaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        # Prevents exception on case creation
        contacts_data = validated_data.pop("contacts", [])
        case = Case.objects.create(**validated_data)
        Contact.process_contacts(case, contacts_data)
        self.start_workflow(case)
        return Response(CaseSerializer(case).data, status=201)

    def start_workflow(self, case):
        task = task_create_main_worflow_for_case.delay(case_id=case.id)
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
        documents = CaseDocument.objects.filter(case=case)
        serializer = CaseDocumentSerializer(documents, many=True)
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
    )
    def get_workflow_options(self, request):
        serializer = WorkflowOptionSerializer(
            WorkflowOption.objects.all(),
            many=True,
        )
        return Response(serializer.data)
