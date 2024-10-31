from apps.events.models import CaseEvent
from rest_framework import serializers


class CaseEventSerializer(serializers.ModelSerializer):
    event_values = serializers.DictField()
    event_variables = serializers.DictField()

    class Meta:
        model = CaseEvent
        fields = (
            "id",
            "event_values",
            "event_variables",
            "created",
            "type",
            "emitter_id",
            "case",
        )
