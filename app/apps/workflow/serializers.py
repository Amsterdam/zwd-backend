import re

from apps.cases.models import Case
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import empty

from .models import CaseUserTask, CaseWorkflow, GenericCompletedTask


class CaseUserTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseUserTask
        fields = (
            "id",
            "task_id",
            "task_name",
            "name",
            "form",
            "roles",
            "due_date",
            "owner",
            "created",
            "updated",
            "completed",
        )


class CaseWorkflowSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = CaseWorkflow
        fields = (
            "id",
            "case",
            "workflow_type",
            "workflow_version",
            "workflow_theme_name",
            "workflow_message_name",
            "data",
            "tasks",
        )

    @extend_schema_field(CaseUserTaskSerializer(many=True))
    def get_tasks(self, obj):
        return CaseUserTaskSerializer(
            CaseUserTask.objects.filter(
                workflow=obj,
                completed=False,
            ).order_by("id"),
            many=True,
            context=self.context,
        ).data


class GenericCompletedTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericCompletedTask
        fields = "__all__"


class GenericCompletedTaskCreateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    case_user_task_id = serializers.CharField()
    case = serializers.PrimaryKeyRelatedField(queryset=Case.objects.all())
    variables = serializers.JSONField()
    description = serializers.CharField(required=False)

    class Meta:
        model = GenericCompletedTask
        exclude = [
            "task_name",
        ]


class WorkflowSpecConfigVerionListSerializer(serializers.DictField):
    def run_validation(self, data=empty):
        def validate_field(field):
            return bool(re.match(r"(\d+\.)+(\d+\.)+(\d+)", field))

        if data is not empty:
            not_valid = [f for f in set(data) if not validate_field(f)]
            if not_valid:
                raise serializers.ValidationError(
                    f"Versioning incorrect: {', '.join(not_valid)}"
                )

        return super().run_validation(data)


class WorkflowSpecConfigVerionSerializer(serializers.Serializer):
    messages = serializers.DictField(required=False, child=serializers.DictField())


class WorkflowSpecConfigThemeSerializer(serializers.Serializer):
    initial_data = serializers.DictField()
    versions = WorkflowSpecConfigVerionListSerializer(
        child=WorkflowSpecConfigVerionSerializer()
    )

    def run_validation(self, data=empty):
        if data is not empty:
            unknown = set(data) - set(self.fields)
            if unknown:
                errors = ["Unknown field: {}".format(f) for f in unknown]
                raise serializers.ValidationError(
                    {
                        "error": errors,
                    }
                )

        return super().run_validation(data)


class WorkflowSpecConfigThemeTypeSerializer(serializers.Serializer):
    process_vve_ok = WorkflowSpecConfigThemeSerializer(required=False)

    def run_validation(self, data=empty):
        if data is not empty:
            unknown = set(data) - set(self.fields)
            if unknown:
                errors = ["Unknown field: {}".format(f) for f in unknown]
                raise serializers.ValidationError(
                    {
                        "error": errors,
                    }
                )

        return super().run_validation(data)


class WorkflowSpecConfigSerializer(serializers.Serializer):
    default = WorkflowSpecConfigThemeTypeSerializer()

    def run_validation(self, data=empty):
        if data is not empty:
            unknown = set(data) - set(self.fields)
            if unknown:
                errors = ["Unknown field: {}".format(f) for f in unknown]
                raise ValueError

        return super().run_validation(data)
