from django.utils import timezone
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponse
from openpyxl import Workbook

admin.site.unregister(User)


@admin.action(description="Geselecteerde gebruikers exporteren inclusief groepen")
def export_selected_users_to_excel(modeladmin, request, queryset):
    wb = Workbook()
    wb_sheet = wb.active
    wb_sheet.title = "Gebruikers inclusief groepen"

    headers = [
        "Naam",
        "E-mailadres",
        "Groepen",
        "Datum account aangemaakt",
        "Laatste login",
        "Actief",
    ]
    wb_sheet.append(headers)

    for u in queryset.prefetch_related("groups"):
        date_joined = (
            timezone.localtime(u.date_joined).strftime("%d-%m-%Y %H:%M:%S")
            if u.date_joined
            else ""
        )
        last_login = (
            timezone.localtime(u.last_login).strftime("%d-%m-%Y %H:%M:%S")
            if u.last_login
            else ""
        )
        full_name = f"{u.first_name} {u.last_name}".strip()
        wb_sheet.append(
            [
                full_name,
                u.email,
                ", ".join(g.name for g in u.groups.all()),
                date_joined,
                last_login,
                "Ja" if u.is_active else "Nee",
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="gebruikers_groepen.xlsx"'
    wb.save(response)
    return response


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "last_login",
        "date_joined",
    )
    actions = [export_selected_users_to_excel]
