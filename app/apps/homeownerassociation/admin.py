from django.contrib import admin

from apps.homeownerassociation.models import HomeownerAssociation
from apps.homeownerassociation.models import Contact


class ContactInline(admin.TabularInline):
    model = (
        Contact.homeowner_associations.through
    )  # Use the through model for the Many-to-Many relationship
    extra = (
        1  # Optionally, specify how many empty forms to display for adding new contacts
    )
    verbose_name = "Contact"
    verbose_name_plural = "Contacts"


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
    inlines = [ContactInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "fullname", "email", "phone", "role")
    search_fields = ("id", "fullname", "email", "phone", "role")
