from django.contrib import admin

from apps.workflow.models import CaseWorkflow
from apps.workflow.tasks import task_create_main_worflow_for_case, task_start_workflow
from .models import Case, CaseDocument, CaseStatus
from django.db import transaction


@admin.action(description="Restart main workflow and delete existing workflows")
def start_workflow(modeladmin, request, queryset):
    for case in queryset:
        with transaction.atomic():
            existing_case_workflows = CaseWorkflow.objects.filter(
                case=case, main_workflow=True
            )
            for existing_workflow in existing_case_workflows:
                existing_workflow.delete()
            task = task_create_main_worflow_for_case.delay(
                case_id=case.id, data={"initiated_by": request.user.id}
            )
            task.wait(timeout=None, interval=0.5)
            start_workflow_task = task_start_workflow.delay(
                CaseWorkflow.objects.get(case=case).id
            )
            start_workflow_task.wait(timeout=None, interval=0.5)


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "advice_type",
        "status",
        "homeowner_association",
        "created",
        "updated",
        "end_date",
    )
    search_fields = ("id",)
    list_filter = (
        "created",
        "end_date",
        "advice_type",
        "status",
    )
    actions = [start_workflow]


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "document", "name")
    search_fields = ("id",)


@admin.register(CaseStatus)
class CaseStatusAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    search_fields = ("name",)
