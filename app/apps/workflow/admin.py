from django.contrib import admin
from .models import CaseWorkflow


@admin.register(CaseWorkflow)
class CaseWorkflowAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case"
    )
