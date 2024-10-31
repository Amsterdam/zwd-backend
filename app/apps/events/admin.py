from django.contrib import admin

from apps.events.models import CaseEvent


admin.site.register(
    CaseEvent,
    admin.ModelAdmin,
    readonly_fields=("created", "event_values"),
    list_display=(
        "id",
        "emitter",
        "emitter_id",
        "emitter_type",
        "type",
        "created",
    ),
    list_filter=(
        "created",
        "type",
    ),
    search_fields=("emitter_id",),
)
