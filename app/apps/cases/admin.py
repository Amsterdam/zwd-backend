from django.contrib import admin
from .models import Case
# Register your models here.


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "description"
    )
