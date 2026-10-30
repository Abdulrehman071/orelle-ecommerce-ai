from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Customer management - spec section 40"""
    list_display = ['email', 'first_name', 'last_name', 'phone', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Storefront Info', {'fields': ('phone', 'role', 'date_of_birth')}),
    )


admin.site.register(Address)
