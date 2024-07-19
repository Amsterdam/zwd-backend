from django.contrib import admin
from .models import CaseUserTask, CaseWorkflow


@admin.register(CaseWorkflow)
class CaseWorkflowAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case"
    )
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
