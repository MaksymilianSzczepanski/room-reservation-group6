from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active", "group_list")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = DjangoUserAdmin.fieldsets
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Grupy i uprawnienia", {"fields": ("groups", "user_permissions")}),
    )

    @admin.display(description="Grupy")
    def group_list(self, obj):
        return ", ".join(obj.groups.values_list("name", flat=True)) or "-"
