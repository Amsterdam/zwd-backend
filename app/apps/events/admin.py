from django.contrib import admin

from apps.events.models import CaseEvent


@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    readonly_fields = ("created", "event_values")
    list_display = (
        "id",
        "emitter",
        "emitter_id",
        "emitter_type",
        "type",
        "description",
        "created",
    )
    list_filter = (
        "created",
        "type",
    )
    search_fields = (
        "emitter_id",
        "case__id",
    )

    def description(self, obj):
        return obj.event_values.get("description", "")

    description.short_description = "Description"
