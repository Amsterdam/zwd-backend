from django.contrib import admin

from apps.homeownerassociation.models import HomeownerAssociation


@admin.register(HomeownerAssociation)
class HomeownerAssociationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "build_year",
        "number_of_appartments",
        "created_at",
        "updated_at",
    )
    search_fields = ("id",)
