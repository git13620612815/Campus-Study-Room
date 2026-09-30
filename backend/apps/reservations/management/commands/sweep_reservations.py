from django.core.management.base import BaseCommand

from apps.reservations.services import sweep


class Command(BaseCommand):
    help = '将超时未签到的预约记为爽约，并将已结束的签到记为完成'

    def handle(self, *args, **options):
        result = sweep()
        self.stdout.write(
            f"爽约 {result['expired']}，完成 {result['completed']}，清理图片 {result['images']}"
        )
