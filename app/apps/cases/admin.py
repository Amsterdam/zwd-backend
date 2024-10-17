from django.contrib import admin
from .models import Case


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
