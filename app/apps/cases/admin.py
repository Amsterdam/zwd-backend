from django.contrib import admin
from .models import Case, CaseDocument


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "description",
        "advice_type",
        "homeowner_association",
        "created",
        "updated",
    )
    search_fields = ("id",)


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "document", "name")
    search_fields = ("id",)
