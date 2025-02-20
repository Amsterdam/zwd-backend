from rest_framework import serializers
from .models import Advisor


class CaseAdvisorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Advisor
        fields = ("id", "name")
