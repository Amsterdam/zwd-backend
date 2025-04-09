import logging
import django_filters
from rest_framework import status
from apps.cases.models import CaseStatus
from apps.homeownerassociation.models import District, Wijk
from utils.pagination import CustomPagination
from apps.cases.serializers import CaseDocumentWithTaskSerializer
from apps.workflow.task_completion import (
    complete_generic_user_task_and_create_new_user_tasks,
)
from apps.workflow.utils import (
    get_bpmn_models,
    get_bpmn_file,
    get_bpmn_model_versions_and_files,
    map_variables_on_task_spec_form,
)
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from .models import CaseUserTask, GenericCompletedTask
from .serializers import (
    BpmnModelListSerializer,
    BpmnModelSerializer,
    CaseUserTaskListSerializer,
    GenericCompletedTaskCreateSerializer,
    GenericCompletedTaskSerializer,
)
from django_filters.rest_framework import DjangoFilterBackend


logger = logging.getLogger(__name__)


class CaseUserTaskFilter(django_filters.FilterSet):
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
    status = django_filters.ModelMultipleChoiceFilter(
        queryset=CaseStatus.objects.all(),
        method="filter_status",
        to_field_name="name",
    )

    homeowner_association_name = django_filters.CharFilter(
        field_name="case__homeowner_association__name",
        lookup_expr="icontains",
    )

    def filter_district(self, queryset, _, value):
        if value:
            return queryset.filter(
                case__homeowner_association__district__in=value,
            )
        return queryset

    def filter_wijk(self, queryset, _, value):
        if value:
            return queryset.filter(
                case__homeowner_association__wijk__in=value,
            )
        return queryset

    def filter_status(self, queryset, _, value):
        if value:
            return queryset.filter(
                case__status__in=value,
            )
        return queryset


class CaseUserTaskViewSet(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    serializer_class = CaseUserTaskListSerializer
    queryset = CaseUserTask.objects.filter(completed=False).prefetch_related("case")
    pagination_class = CustomPagination
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend)
    ordering_fields = ["id", "created"]
    filterset_class = CaseUserTaskFilter


class GenericCompletedTaskViewSet(viewsets.GenericViewSet):
    serializer_class = GenericCompletedTaskSerializer
    queryset = GenericCompletedTask.objects.all()

    @extend_schema(description="Complete GenericCompletedTask", responses={200: None})
    @action(
        detail=False,
        url_path="complete",
        methods=["post"],
        serializer_class=GenericCompletedTaskCreateSerializer,
    )
    def complete_task(self, request):
        serializer = GenericCompletedTaskCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            return self._complete_task_common(serializer)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        url_path="complete-file-task",
        methods=["post"],
        serializer_class=CaseDocumentWithTaskSerializer,
    )
    def complete_file_task(self, request):
        serializer = CaseDocumentWithTaskSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            return self._complete_task_common(serializer, save_document=True)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def _complete_task_common(self, serializer, save_document=False):
        data = serializer.validated_data
        case_user_task_id = data.pop("case_user_task_id")
        author = data.pop("author")
        variables = data.get("variables", {})
        task = CaseUserTask.objects.get(id=case_user_task_id, completed=False)

        if task.requires_review and author.id == task.initiated_by.id:
            return Response(
                {"detail": "You are not authorized to complete this task"},
                status=status.HTTP_403_FORBIDDEN,
            )

        from apps.workflow.user_tasks import get_task_by_name

        user_task_type = get_task_by_name(task.task_name)
        user_task = user_task_type(task)

        if user_task and user_task.mapped_form_data(variables):
            variables["mapped_form_data"] = user_task.mapped_form_data(variables)
        else:
            variables["mapped_form_data"] = map_variables_on_task_spec_form(
                variables, task.form
            )

        # Only save the document if it is a file task so the file gets uploaded
        if save_document:
            variables["mapped_form_data"]["document_name"] = {
                "label": "Document",
                "value": serializer.validated_data.get("name"),
            }
            serializer.save()
        variables["initiated_by"] = author.id
        task_data = {
            "case_user_task_id": case_user_task_id,
            "description": task.name,
            "task_name": task.task_name,
            "variables": variables,
            "case": task.case,
            "author": author,
        }

        case_user_task = GenericCompletedTask.objects.create(**task_data)
        complete_generic_user_task_and_create_new_user_tasks(case_user_task)

        return Response(
            {"message": f"CaseUserTask {case_user_task_id} has been completed"},
            status=status.HTTP_200_OK,
        )


class BpmnViewSet(viewsets.GenericViewSet):
    pagination_class = None

    @extend_schema(
        description="Get all BPMN model names",
        responses={200: BpmnModelListSerializer},  # Array of strings
    )
    def list(self, request):
        try:
            models = get_bpmn_models()  # Returns a list of model names
            return Response(models, status=200)
        except Exception as e:
            logger.error(f"Failed to fetch BPMN model names: {e}")
            return Response(
                {"detail": "An error occurred while fetching BPMN model names"},
                status=500,
            )

    @extend_schema(
        description="Get versions and filenames for a specific model",
        responses={200: BpmnModelSerializer(many=True)},
    )
    @action(detail=False, url_path="(?P<model_name>[^/]+)", methods=["get"])
    def get_model_versions(self, request, model_name):
        try:
            versions = get_bpmn_model_versions_and_files(model_name)
            if isinstance(versions, dict) and "error" in versions:
                return Response(versions, status=404)
            return Response(versions, status=200)
        except Exception as e:
            logger.error(f"Failed to fetch BPMN models: {e}")
            return Response(
                {"detail": "An error occurred while fetching BPMN models."}, status=500
            )

    @extend_schema(
        description="Get a specific BPMN workflow file",
        responses={200: None},
    )
    @action(
        detail=False,
        url_path="(?P<model_name>[^/]+)/file/(?P<version>[^/]+)",
        methods=["get"],
    )
    def get_bpmn_file(self, request, model_name, version):
        content = get_bpmn_file(model_name, version)
        return HttpResponse(content, content_type="application/xml")
