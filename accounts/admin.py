from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import AdminAddUserForm, AdminChangeUserForm
from .models import Address, User


class AddressInline(admin.TabularInline):
    """A customer's saved addresses — admin-only; staff see order addresses."""

    model = Address
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = AdminAddUserForm
    form = AdminChangeUserForm
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ("ThoughtTronix", {"fields": ("job_title",)}),
    )
    list_display = ("username", "email", "job_title", "is_staff")
    inlines = [AddressInline]
