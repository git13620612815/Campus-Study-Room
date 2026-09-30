from django.contrib import admin

from apps.common.models import OperationLog, SystemConfig


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'admin', 'action', 'target_type', 'target_id', 'detail')
    list_filter = ('action',)
