from django.contrib import admin
from .models import Case, CaseDocument, CaseStatus


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
