# leases/admin.py
from django.contrib import admin
from .models import Property, Tenant, Lease
from django.utils.translation import gettext_lazy as _
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('address', 'city', 'country')
    search_fields = ('address', 'city', 'country')
    list_filter = ('country', 'city')
    verbose_name = _("Property")
    verbose_name_plural = _("Properties")


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone')
    search_fields = ('first_name', 'last_name', 'email')
    # Убрали 'city' из list_filter
    # list_filter = ('city',)  ← Ошибка!


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ('property', 'tenant', 'start_date', 'end_date', 'monthly_rent', 'payment_day')
    list_filter = ('start_date', 'end_date', 'property', 'tenant')
    search_fields = ('property__address', 'tenant__first_name', 'tenant__last_name')
    date_hierarchy = 'start_date'