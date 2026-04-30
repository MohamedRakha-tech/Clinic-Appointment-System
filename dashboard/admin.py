from django.contrib import admin

# Register your models here.
# dashboard/admin.py

from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):


    list_display = (
        'timestamp',
        'user',
        'action',
        'target_model',
        'target_id',
        'description',
        'ip_address',
    )


    list_filter = (
        'action',
        'target_model',
        'timestamp',
    )

    
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'description',
        'target_model',
    )


    ordering = ('-timestamp',)


    readonly_fields = (
        'user',
        'action',
        'target_model',
        'target_id',
        'description',
        'ip_address',
        'extra_data',
        'timestamp',
    )


    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False