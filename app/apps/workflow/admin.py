from django.contrib import admin

from .models import CaseUserTask, CaseWorkflow, GenericCompletedTask


@admin.register(CaseWorkflow)
class CaseWorkflowAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case",
        "main_workflow",
        "workflow_type",
        "workflow_version",
        "case_state_type",
        "completed",
    )

    search_fields = ("case__id",)

    list_filter = ("main_workflow", "completed")


@admin.register(CaseUserTask)
class CaseTaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case",
        "name",
        "task_name",
        "completed",
        "workflow",
        "owner",
    )
    search_fields = (
        "case__id",
        "name",
        "task_name",
    )
    list_filter = ("completed", "name")


@admin.register(GenericCompletedTask)
class GenericCompletedTaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case",
        "date_added",
        "description",
        "author",
        "case_user_task_id",
    )
    search_fields = (
        "case__id",
        "description",
    )
    list_filter = (
        "date_added",
        "description",
        "task_name",
    )
