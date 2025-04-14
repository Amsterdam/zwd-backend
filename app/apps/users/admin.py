from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

print("CustomUserAdmin loaded")

admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "email",
        "is_staff",
        "last_login",
        "date_joined",
    )
