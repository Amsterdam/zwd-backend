from apps.workflow.utils import (
    get_bpmn_file,
    get_bpmn_files,
    map_variables_on_task_spec_form,
)
from django.http import HttpResponse, HttpResponseBadRequest
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny

from .models import CaseUserTask, GenericCompletedTask
from .serializers import (
    CaseUserTaskSerializer,
    GenericCompletedTaskCreateSerializer,
    GenericCompletedTaskSerializer,
)


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

    def get_permissions(self):
        if self.action == "get_bpmn_file":
            return [AllowAny()]
        return super().get_permissions()

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

    @action(detail=False, url_path="workflow_files", methods=["get"])
    @permission_classes([AllowAny])
    def get_workflow_files(self, request):
        return Response(get_bpmn_files())

    @action(
        detail=False,
        url_path="workflow_files/(?P<workflow_type>[^/]+)/(?P<version>[^/]+)/(?P<file_name>[^/]+)",
        methods=["get"],
    )
    @permission_classes([AllowAny])
    def get_bpmn_file(self, request, workflow_type, version, file_name):
        print(f"Request received for {workflow_type}/{version}/{file_name}")
        content = get_bpmn_file(workflow_type, version, file_name)
        # Return the file content as an XML response
        return HttpResponse(content, content_type="application/xml")
