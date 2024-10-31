from django.contrib import admin

from apps.homeownerassociation.models import (
    HomeownerAssociation,
    Contact,
    Neighborhood,
    Owner,
    District,
)


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
        "created",
        "updated",
    )
    search_fields = ("id",)
    inlines = [ContactInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "fullname", "email", "phone", "role")
    search_fields = ("id", "fullname", "email", "phone", "role")


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_homeowner_association_name",
        "type",
        "name",
        "number_of_appartments",
    )
    search_fields = (
        "id",
        "type",
        "name",
        "number_of_appartments",
        "homeowner_association__name",
    )

    def get_homeowner_association_name(self, obj):
        return obj.homeowner_association.name


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("id", "name")


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "district")
    search_fields = ("id", "name", "district__name")
