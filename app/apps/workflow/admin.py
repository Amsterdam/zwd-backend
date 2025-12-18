from django.contrib import admin

from .models import (
    CaseUserTask,
    CaseWorkflow,
    CaseWorkflowStateHistory,
    GenericCompletedTask,
    WorkflowOption,
)


@admin.action(description="Restore workflow state to selected history point")
def restore_history(modeladmin, request, queryset):
    for workflow_history in queryset:
        workflow_history.restore()


@admin.register(CaseWorkflow)
class CaseWorkflowAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case",
        "main_workflow",
        "workflow_type",
        "workflow_version",
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


@admin.register(WorkflowOption)
class WorkflowOptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "message_name",
        "enabled_on_case_closed",
    )
    list_filter = ("enabled_on_case_closed",)


@admin.register(CaseWorkflowStateHistory)
class CaseWorkflowStateHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workflow",
        "created_at",
        "tasks_created",
        "tasks_deleted",
    )
    search_fields = ("workflow__id",)
    list_filter = ("created_at",)

    readonly_fields = (
        "workflow",
        "created_at",
        "tasks_created",
        "tasks_deleted",
    )
    actions = [restore_history]

    def tasks_created(self, history_obj):
        return ", ".join(history_obj.get_tasks_to_create())

    def tasks_deleted(self, history_obj):
        return ", ".join(history_obj.get_task_to_delete())

    tasks_created.short_description = "Tasks that get recreated"
    tasks_deleted.short_description = "Tasks that get deleted"
