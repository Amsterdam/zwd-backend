from django import forms
from django.contrib import admin
from .models import Case
from django_bpmn.widget import BPMNWidget


class BPMNForm(forms.ModelForm):
    model = Case
    widgets = {"description": BPMNWidget()}
    fields = "__all__"


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "description")
    search_fields = ("id",)
    form = BPMNForm

    # Additional debugging information
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Print the fields to the console for debugging
        print("***")
        print(form.__dict__)
        return form
