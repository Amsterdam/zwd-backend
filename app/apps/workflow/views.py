import copy
import logging
from rest_framework import status
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
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from .models import CaseUserTask, CaseWorkflow, GenericCompletedTask
from .serializers import (
    BpmnModelListSerializer,
    BpmnModelSerializer,
    CaseUserTaskListSerializer,
    GenericCompletedTaskCreateSerializer,
    GenericCompletedTaskSerializer,
    UndoSerializer,
)
from SpiffWorkflow import TaskState

logger = logging.getLogger(__name__)


class CaseUserTaskViewSet(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    serializer_class = CaseUserTaskListSerializer
    queryset = CaseUserTask.objects.filter(completed=False).prefetch_related("case")


class GenericCompletedTaskViewSet(viewsets.GenericViewSet):
    serializer_class = GenericCompletedTaskSerializer
    queryset = GenericCompletedTask.objects.all()

    @action(
        detail=False,
        url_path="undo",
        methods=["post"],
        serializer_class=UndoSerializer,
    )
    def undo_task(self, request):
        serializer = UndoSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            case_workflow = CaseWorkflow.objects.get(
                id=serializer.validated_data.get("workflow_id")
            )
            case_workflow.serialized_workflow_state = copy.deepcopy(
                case_workflow.previous_serialized_workflow_state
            )
            case_workflow.data = copy.deepcopy(case_workflow.previous_data)
            case_workflow.completed = False
            case_workflow.save()
            wf = case_workflow._get_or_restore_workflow_state()
            case_user_tasks = CaseUserTask.objects.filter(
                workflow=case_workflow, completed=False
            )
            case_user_tasks.delete()
            ready_tasks = wf.get_tasks(state=TaskState.READY)
            for ready_task in ready_tasks:
                case_user_task = CaseUserTask.objects.filter(task_id=ready_task.id)
                if case_user_task:
                    case_user_task.delete()
            case_workflow._create_user_tasks(wf)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
