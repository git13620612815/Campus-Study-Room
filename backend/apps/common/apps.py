from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    verbose_name = '系统'

    def ready(self):
        import sys

        from django.db.backends.signals import connection_created

        def configure_sqlite(sender, connection, **kwargs):
            if connection.vendor != 'sqlite' or 'test' in sys.argv:
                return
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA journal_mode=WAL;')

        connection_created.connect(configure_sqlite, dispatch_uid='campus_sqlite_wal')
