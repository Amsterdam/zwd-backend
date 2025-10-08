from time import sleep
from django.contrib import admin

from apps.workflow.models import CaseWorkflow
from apps.workflow.tasks import task_create_main_worflow_for_case, task_start_workflow
from .models import (
    ActivationTeam,
    Case,
    CaseClose,
    CaseCloseReason,
    CaseDocument,
    CaseStatus,
)
from django.db import transaction


@admin.action(description="Fix request_date from created")
def fix_request_date(modeladmin, request, queryset):
    updated_count = 0
    for case in queryset.iterator():
        if case.request_date != case.created.date():
            case.request_date = case.created.date()
            case.save()
            updated_count += 1
    modeladmin.message_user(request, f"Updated request_date for {updated_count} cases.")


@admin.action(description="Restart main workflow and delete existing workflows")
def restart_workflow(modeladmin, request, queryset):
    for case in queryset:
        with transaction.atomic():
            sleep(1)
            existing_case_workflows = CaseWorkflow.objects.filter(case=case)
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
        "legacy_id",
        "application_type",
        "advice_type",
        "status",
        "homeowner_association",
        "created",
        "updated",
        "request_date",
        "end_date",
    )
    search_fields = ("id", "legacy_id")
    list_filter = (
        "application_type",
        "advice_type",
        "status",
        "created",
        "updated",
        "request_date",
        "end_date",
    )
    actions = [restart_workflow, fix_request_date]


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "document", "name")
    search_fields = ("id",)


@admin.register(CaseStatus)
class CaseStatusAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "position",
    )
    list_display_links = ("id",)
    list_editable = ("position",)
    search_fields = ("name",)


@admin.register(ActivationTeam)
class ActivationTeamAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "type", "meeting_date", "created")
    search_fields = ("case__id",)
    list_filter = ("type",)


@admin.register(CaseCloseReason)
class CaseCloseReasonAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_successful")
    search_fields = ("name",)
    list_filter = ("is_successful",)


@admin.register(CaseClose)
class CaseCloseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case",
        "reason",
        "case_user_task_id",
        "created",
        "author",
    )
    search_fields = ("case__id",)
    list_filter = ("reason",)
