import mimetypes
from apps.advisor.serializers import UpdateCaseAdvisorSerializer
from apps.homeownerassociation.models import Contact, District, Neighborhood, Wijk
from apps.events.serializers import CaseEventSerializer
from apps.events.mixins import CaseEventsMixin
from apps.advisor.mixins import CaseAdvisorMixin
from apps.workflow.models import CaseWorkflow, WorkflowOption
from apps.workflow.serializers import CaseWorkflowSerializer, WorkflowOptionSerializer
from rest_framework import mixins, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import (
    ActivationTeam,
    AdviceType,
    ApplicationType,
    Case,
    CaseClose,
    CaseCloseReason,
    CaseDocument,
    CaseCommunicationNote,
    CaseStatus,
)
from .serializers import (
    CaseCloseReasonSerializer,
    CaseCloseSerializer,
    CaseCreateSerializer,
    CaseDocumentSerializer,
    CaseUpdateSerializer,
    CaseSerializer,
    CaseListSerializer,
    CaseStatusSerializer,
    StartWorkflowSerializer,
    CaseDocumentNameUpdateSerializer,
    CaseCommunicationNoteSerializer,
    CaseCommunicationNoteCreateSerializer,
    CaseCommunicationNoteUpdateSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.http import FileResponse
from apps.workflow.tasks import task_create_main_worflow_for_case
from apps.workflow.tasks import task_start_workflow
from apps.advisor.models import Advisor
from utils.pagination import CustomPagination
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from django.db import transaction
from django.db.models import Q


class CaseFilter(django_filters.FilterSet):
    advice_type = django_filters.ChoiceFilter(
        field_name="advice_type",
        choices=AdviceType.choices(),
    )
    application_type = django_filters.ChoiceFilter(
        field_name="application_type",
        choices=ApplicationType.choices(),
    )
    closed = django_filters.BooleanFilter(method="filter_closed_cases")
    district = django_filters.ModelMultipleChoiceFilter(
        queryset=District.objects.all(),
        method="filter_district",
        to_field_name="name",
    )
    wijk = django_filters.ModelMultipleChoiceFilter(
        queryset=Wijk.objects.all(),
        method="filter_wijk",
        to_field_name="name",
    )
    neighborhood = django_filters.ModelMultipleChoiceFilter(
        queryset=Neighborhood.objects.all(),
        method="filter_neighborhood",
        to_field_name="name",
    )
    status = django_filters.ModelMultipleChoiceFilter(
        queryset=CaseStatus.objects.all(),
        method="filter_status",
        to_field_name="name",
    )
    advisor = django_filters.ModelMultipleChoiceFilter(
        queryset=Advisor.objects.all(),
        method="filter_advisor",
    )
    search = django_filters.CharFilter(method="filter_search", label="Search")
    request_date_range = django_filters.DateFromToRangeFilter(field_name="request_date")
    end_date_range = django_filters.DateFromToRangeFilter(field_name="end_date")
    is_small_hoa = django_filters.BooleanFilter(
        method="filter_is_small_hoa", label="HOA has <= 12 apartments"
    )

    def filter_closed_cases(self, queryset, _, value):
        if value:
            return queryset.filter(end_date__isnull=False)
        return queryset.filter(end_date__isnull=True)

    def filter_district(self, queryset, _, value):
        if value:
            return queryset.filter(
                homeowner_association__district__in=value,
            )
        return queryset

    def filter_wijk(self, queryset, _, value):
        if value:
            return queryset.filter(
                homeowner_association__wijk__in=value,
            )
        return queryset

    def filter_neighborhood(self, queryset, _, value):
        if value:
            return queryset.filter(
                homeowner_association__neighborhood__in=value,
            )
        return queryset

    def filter_status(self, queryset, _, value):
        if value:
            return queryset.filter(
                status__in=value,
            )
        return queryset

    def filter_advisor(self, queryset, _, value):
        if value:
            return queryset.filter(
                advisor__in=value,
            )
        return queryset

    def filter_search(self, queryset, _, value):
        """
        Filter cases based on a search term that matches either
        homeowner_association__name, legacy_id, id or prefixed_dossier_id.
        """
        try:
            case_id = int(value)
        except ValueError:
            case_id = None

        return queryset.filter(
            Q(homeowner_association__name__icontains=value)
            | Q(legacy_id__icontains=value)
            | Q(id=case_id)
            | Q(prefixed_dossier_id__iexact=value)
        )

    def filter_is_small_hoa(self, queryset, _, value):
        """
        Filter cases based on the 'is_small' property of the HomeownerAssociation.
        """
        if value is True:
            return queryset.filter(homeowner_association__number_of_apartments__lte=12)
        if value is False:
            return queryset.filter(homeowner_association__number_of_apartments__gt=12)
        return queryset


class CaseViewSet(
    CaseEventsMixin,
    CaseAdvisorMixin,
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
):
    queryset = Case.objects.all().prefetch_related("homeowner_association")
    serializer_class = CaseSerializer
    pagination_class = CustomPagination
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend)
    ordering_fields = [
        "id",
        "request_date",
        "updated",
        "homeowner_association__name",
        "legacy_id",
        "status",
    ]
    filterset_class = CaseFilter

    def get_serializer_class(self):
        if self.action == "create_document" or self.action == "get_documents":
            return CaseDocumentSerializer
        elif self.action == "create":
            return CaseCreateSerializer
        elif self.action == "list":
            return CaseListSerializer
        elif self.action == "events":
            return CaseEventSerializer
        elif self.action in ["partial_update", "update"]:
            return CaseUpdateSerializer

        return CaseSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                many=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="workflows")
    def get_workflows(self, request, pk=None):
        case = self.get_object()
        workflows = CaseWorkflow.objects.filter(
            case=case, completed=False, tasks__isnull=False
        ).distinct()
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
        activation_team_data = validated_data.pop("activation_team", None)

        with transaction.atomic():
            case = Case.objects.create(**validated_data)
            Contact.process_contacts(case.homeowner_association, contacts_data)
            if (
                case.application_type == ApplicationType.ACTIVATIONTEAM.value
                and activation_team_data
            ):
                ActivationTeam.objects.create(case=case, **activation_team_data)

        # Start the main workflow for the case
        self.start_workflow(case, request.user.id)

        return Response(CaseSerializer(case).data, status=201)

    def start_workflow(self, case, user_id):
        task = task_create_main_worflow_for_case.delay(
            case_id=case.id, data={"initiated_by": user_id}
        )
        task.wait(timeout=None, interval=0.5)
        start_workflow_task = task_start_workflow.delay(
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

    @extend_schema(
        methods=["get"],
        responses={200: CaseCommunicationNoteSerializer(many=True)},
        description="List communication notes for a case",
    )
    @extend_schema(
        methods=["post"],
        request=CaseCommunicationNoteCreateSerializer,
        responses={201: CaseCommunicationNoteSerializer},
        description="Create a communication note for a case",
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="communication-notes",
        filter_backends=[],
        pagination_class=None,
    )
    def communication_notes(self, request, pk=None):
        case = self.get_object()

        if request.method == "GET":
            notes = CaseCommunicationNote.objects.filter(case=case).order_by("-date")
            serializer = CaseCommunicationNoteSerializer(notes, many=True)
            return Response(serializer.data)

        serializer = CaseCommunicationNoteCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        note = CaseCommunicationNote.objects.create(
            case=case, **serializer.validated_data
        )
        return Response(
            CaseCommunicationNoteSerializer(note).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        methods=["patch"],
        request=CaseCommunicationNoteUpdateSerializer,
        responses={200: CaseCommunicationNoteSerializer},
        description="Update a communication note",
    )
    @extend_schema(
        methods=["delete"],
        responses={204: None},
        description="Delete a communication note",
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path="communication-notes/(?P<note_id>[^/.]+)",
    )
    def communication_note_detail(self, request, pk=None, note_id=None):
        case = self.get_object()
        note = get_object_or_404(CaseCommunicationNote, case=case, id=note_id)

        if request.method == "PATCH":
            serializer = CaseCommunicationNoteUpdateSerializer(
                note, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(CaseCommunicationNoteSerializer(note).data)

        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        request=CaseDocumentNameUpdateSerializer,
        responses=CaseDocumentNameUpdateSerializer,
        description="Update the name of a document",
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="documents/(?P<doc_id>[^/.]+)/update-name",
    )
    def update_document_name(self, request, pk=None, doc_id=None):
        case = self.get_object()
        case_document = get_object_or_404(CaseDocument, case=case, id=doc_id)

        serializer = CaseDocumentNameUpdateSerializer(
            case_document, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            task = task_start_workflow.delay(case_workflow.id)
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
        detail=True,
        url_path="processes",
        url_name="processes",
        methods=["get"],
        serializer_class=WorkflowOptionSerializer,
        pagination_class=None,
    )
    def get_workflow_options(self, request, pk):
        case = self.get_object()
        case_closed = case.end_date is not None
        query_set = WorkflowOption.objects.all()
        if case_closed:
            query_set = query_set.filter(enabled_on_case_closed=True)
        serializer = WorkflowOptionSerializer(query_set, many=True)
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


class CaseStatusViewset(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = CaseStatus.objects.all()
    serializer_class = CaseStatusSerializer

    def list(self, _, *args, **kwargs):
        names = self.get_queryset().values_list("name", flat=True).distinct()
        return Response(list(names))


class CaseCloseViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    queryset = CaseClose.objects.all()
    serializer_class = CaseCloseSerializer
    pagination_class = CustomPagination

    @extend_schema(
        responses=CaseCloseReasonSerializer,
        description="Retrieve reasons to close a case",
    )
    @action(detail=False, methods=["get"], url_path="reasons")
    def reasons(self, request, *args, **kwargs):
        """
        Endpoint to list all case close reasons.
        """
        reasons = CaseCloseReason.objects.all()
        serializer = CaseCloseReasonSerializer(reasons, many=True)
        return Response(serializer.data)
