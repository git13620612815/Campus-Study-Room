from django.conf import settings
from django.db import models


class SystemConfig(models.Model):
    key = models.CharField(max_length=64, unique=True)
    value = models.CharField(max_length=255)

    class Meta:
        db_table = 'system_configs'
        verbose_name = '系统参数'
        verbose_name_plural = '系统参数'

    def __str__(self):
        return f'{self.key}={self.value}'


class OperationLog(models.Model):
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='operation_logs',
    )
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=32)
    target_id = models.CharField(max_length=32)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'operation_logs'
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} {self.target_type}:{self.target_id}'
