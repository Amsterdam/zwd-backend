from apps.advisor.models import Advisor
from django.contrib import admin


@admin.register(Advisor)
class AdvisorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "enabled",
        "created_at",
        "updated_at",
        "advice_type_energieadvies",
        "advice_type_hbo",
        "small_hoa",
    )
