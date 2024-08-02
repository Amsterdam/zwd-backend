from apps.workflow.utils import map_variables_on_task_spec_form
from django.http import HttpResponse, HttpResponseBadRequest
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action

from .models import CaseUserTask, GenericCompletedTask
from .serializers import (
    GenericCompletedTaskCreateSerializer,
    GenericCompletedTaskSerializer,
)


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
