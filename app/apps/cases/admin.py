from time import sleep
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from openpyxl import Workbook

from apps.homeownerassociation.models import HomeownerAssociation
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
from .archive import build_archive_plan, execute_archive_plan
from .retention import (
    filter_retention_expired,
    filter_retention_running,
    filter_successful_expired,
    filter_unsuccessful_expired,
    get_result_label,
    get_retention_expiry_date,
    get_retention_years,
    get_selection_category,
    is_successful,
)
from django.db import transaction


def _format_date(value):
    return value.strftime("%d-%m-%Y") if value else ""


@admin.action(description="Geselecteerde zaken exporteren naar Excel")
def export_queryset_to_excel(modeladmin, request, queryset):
    queryset = queryset.select_related(
        "homeowner_association", "status"
    ).prefetch_related("caseclose_set__reason")

    wb = Workbook()
    wb_sheet = wb.active
    wb_sheet.title = "Zaken"

    headers = [
        "Zaak ID",
        "Dossier ID",
        "Legacy ID",
        "VvE",
        "Aanvraagtype",
        "Adviestype",
        "Status",
        "Aanvraagdatum",
        "Adviseur toegekend op",
        "Einddatum",
        "Resultaat",
        "Succesvol",
        "Bewaartermijn (jaren)",
        "Bewaartermijn verloopt op",
        "Selectiecategorie",
        "Gearchiveerd op",
    ]
    wb_sheet.append(headers)

    for case in queryset:
        if case.end_date:
            successful = "Ja" if is_successful(case) else "Nee"
        else:
            successful = ""
        wb_sheet.append(
            [
                case.id,
                case.prefixed_dossier_id or "",
                case.legacy_id or "",
                case.homeowner_association.name if case.homeowner_association else "",
                case.application_type or "",
                case.advice_type or "",
                case.status.name if case.status else "",
                _format_date(case.request_date),
                _format_date(
                    timezone.localtime(case.advisor_assigned_at)
                    if case.advisor_assigned_at
                    else None
                ),
                _format_date(case.end_date),
                get_result_label(case),
                successful,
                get_retention_years(case) or "",
                _format_date(get_retention_expiry_date(case)),
                get_selection_category(case),
                _format_date(
                    timezone.localtime(case.archived_at) if case.archived_at else None
                ),
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="zwd_zaken_export.xlsx"'
    wb.save(response)
    return response


ARCHIVE_PREVIEW_LIMIT = 50


def _preview(ids):
    return {
        "ids": ids[:ARCHIVE_PREVIEW_LIMIT],
        "remaining": len(ids) - ARCHIVE_PREVIEW_LIMIT,
    }


@admin.action(description="Zaken met verlopen bewaartermijn archiveren")
def archive_cases(modeladmin, request, queryset):
    plan = build_archive_plan(queryset)

    if request.POST.get("post") == "yes":
        if not plan.case_ids:
            modeladmin.message_user(
                request, "Er zijn geen zaken gearchiveerd.", messages.WARNING
            )
            return None
        counts = execute_archive_plan(plan)
        modeladmin.message_user(
            request,
            f"{len(plan.case_ids)} zaken gearchiveerd, {plan.skipped_count} overgeslagen. "
            f"Verwijderd: {counts['workflows']} workflows, {counts['tasks']} taken, "
            f"{counts['documents']} documenten, {counts['completed_tasks']} afgeronde taken, "
            f"{counts['events']} tijdlijn-events en {counts['contacts']} contactpersonen.",
            messages.SUCCESS,
        )
        return None

    # Dry-run: show what will happen without changing anything
    hoa_keep = _preview(plan.hoa_ids_keep_contacts)
    hoa_keep["names"] = HomeownerAssociation.objects.filter(
        id__in=hoa_keep["ids"]
    ).values_list("name", flat=True)
    context = {
        **modeladmin.admin_site.each_context(request),
        "title": "Zaken archiveren",
        "opts": modeladmin.model._meta,
        "plan": plan,
        "counts": plan.counts(),
        "skipped": [
            (label, len(ids), _preview(ids))
            for label, ids in [
                ("Nog niet afgesloten", plan.skipped_open_ids),
                (
                    "Afgesloten, maar de bewaartermijn loopt nog",
                    plan.skipped_not_expired_ids,
                ),
                ("Al eerder gearchiveerd", plan.skipped_archived_ids),
            ]
        ],
        "hoa_keep": hoa_keep,
        # With "select all" the confirmation posts select_across instead of every
        # pk, to stay below DATA_UPLOAD_MAX_NUMBER_FIELDS. Django still requires
        # at least one selected pk to dispatch the action.
        "select_across": request.POST.get("select_across") == "1",
        "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
    }
    return TemplateResponse(
        request, "admin/cases/case/archive_confirmation.html", context
    )


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


class BewaartermijnFilter(admin.SimpleListFilter):
    title = "Bewaartermijn"
    parameter_name = "bewaartermijn"

    def lookups(self, request, model_admin):
        return (
            ("verlopen", "Alle verlopen bewaartermijnen"),
            ("succesvol_5_jaar", "Verlopen: succesvol of geen resultaat (5 jaar)"),
            ("afgebroken_1_jaar", "Verlopen: afgebroken (1 jaar)"),
            ("lopend", "Lopende bewaartermijn"),
        )

    def queryset(self, request, queryset):
        filters = {
            "verlopen": filter_retention_expired,
            "succesvol_5_jaar": filter_successful_expired,
            "afgebroken_1_jaar": filter_unsuccessful_expired,
            "lopend": filter_retention_running,
        }
        filter_function = filters.get(self.value())
        if filter_function:
            return filter_function(queryset)
        return queryset


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
        "archived_at",
    )
    search_fields = ("id", "legacy_id")
    list_filter = (
        BewaartermijnFilter,
        "application_type",
        "advice_type",
        "status",
        "created",
        "updated",
        "request_date",
        "end_date",
        "archived_at",
    )
    autocomplete_fields = ["homeowner_association"]
    actions = [
        restart_workflow,
        fix_request_date,
        export_queryset_to_excel,
        archive_cases,
    ]


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
