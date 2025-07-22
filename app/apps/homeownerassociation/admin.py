from django.contrib import admin

from apps.homeownerassociation.models import (
    HomeownerAssociation,
    Contact,
    Neighborhood,
    Owner,
    District,
    PriorityZipCode,
    Wijk,
)


@admin.action(description="Delete owners and update HOA")
def update_hoa(modeladmin, request, queryset):
    for hoa in queryset:
        hoa.owners.all().delete()
        hoa.update_hoa_admin(hoa.name)


@admin.action(description="Update kvk-nummer")
def update_kvk_number(modeladmin, request, queryset):
    for hoa in queryset:
        hoa.update_kvk_nummer(hoa.name)
    modeladmin.message_user(
        request, f"{queryset.count()} kvk-nummers successfully updated."
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
        "kvk_nummer",
        "created",
        "updated",
    )
    search_fields = ("id", "name")
    inlines = [ContactInline]
    actions = [update_hoa, update_kvk_number]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "fullname", "phone", "role")
    search_fields = ("id", "email", "fullname", "phone", "role")


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


@admin.register(Wijk)
class WijkAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "neighborhood")
    search_fields = ("id", "name", "neighborhood__name")


@admin.register(PriorityZipCode)
class PriorityZipCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "zip_code")
    search_fields = ("id", "zip_code")
