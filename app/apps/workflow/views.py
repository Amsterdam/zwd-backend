import logging
from apps.workflow.utils import (
    get_bpmn_models,
    get_bpmn_file,
    get_bpmn_model_versions_and_files,
    map_variables_on_task_spec_form,
)
from django.http import HttpResponse, HttpResponseBadRequest
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import CaseUserTask, GenericCompletedTask
from .serializers import (
    BpmnModelListSerializer,
    BpmnModelSerializer,
    CaseUserTaskSerializer,
    GenericCompletedTaskCreateSerializer,
    GenericCompletedTaskSerializer,
)

logger = logging.getLogger(__name__)


class CaseUserTaskViewSet(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
):
    serializer_class = CaseUserTaskSerializer
    queryset = CaseUserTask.objects.filter(completed=False)


class GenericCompletedTaskViewSet(viewsets.GenericViewSet):
    serializer_class = GenericCompletedTaskSerializer
    queryset = GenericCompletedTask.objects.all()

    @extend_schema(
        description="Complete GenericCompletedTask",
        responses={200: None},
    )
    @action(
        detail=False,
        url_path="complete",
        methods=["post"],
        serializer_class=GenericCompletedTaskCreateSerializer,
    )
    def complete_task(self, request):
        context = {"request": self.request}

        serializer = GenericCompletedTaskCreateSerializer(
            data=request.data, context=context
        )
        if serializer.is_valid():
            data = serializer.validated_data

            variables = data.get("variables", {})
            task = CaseUserTask.objects.get(
                id=data["case_user_task_id"], completed=False
            )
            from .user_tasks import get_task_by_name

            user_task_type = get_task_by_name(task.task_name)
            user_task = user_task_type(task)
            if user_task and user_task.mapped_form_data(variables):
                variables["mapped_form_data"] = user_task.mapped_form_data(variables)
            else:
                variables["mapped_form_data"] = map_variables_on_task_spec_form(
                    variables, task.form
                )
            data.update(
                {
                    "description": task.name,
                    "task_name": task.task_name,
                    "variables": variables,
                }
            )

            try:
                GenericCompletedTask.objects.create(**data)
                return HttpResponse(
                    f"CaseUserTask {data['case_user_task_id']} has been completed"
                )
            except Exception as e:
                raise e
        return HttpResponseBadRequest("Invalid request")


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
        # Return the file content as an XML response
        return HttpResponse(content, content_type="application/xml")
