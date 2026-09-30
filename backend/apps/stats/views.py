from rest_framework.views import APIView

from apps.common.errors import BusinessError
from apps.common.excel import workbook_response
from apps.common.responses import ok
from apps.common.utils import stat_range
from apps.stats.services import overview, seat_usage, user_activity, utilization
from apps.users.permissions import IsAdmin


def _room_id(request):
    raw = request.query_params.get('room_id')
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise BusinessError('自习室不正确')


class OverviewView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return ok(overview())


class SeatStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        start, end = stat_range(request)
        return ok({'items': seat_usage(start, end, _room_id(request))})


class UserStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        start, end = stat_range(request)
        return ok({'items': user_activity(start, end)})


class UtilizationView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        start, end = stat_range(request)
        return ok(utilization(start, end))


class StatsExportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        start, end = stat_range(request)
        rows = []
        for item in seat_usage(start, end, _room_id(request)):
            rows.append([
                item['room_name'],
                item['zone'],
                item['code'],
                item['span'],
                item['reservation_count'],
                item['checkin_count'],
                item['expired_count'],
                item['occupied_minutes'],
                item['free_minutes'],
                item['reserved_minutes'],
            ])
        return workbook_response(
            ['自习室', '区域', '座位号', '统计起止日期', '预约次数', '签到次数', '爽约次数', '占用分钟', '空闲分钟', '已预约未使用分钟'],
            rows,
            '座位使用统计.xlsx',
            '座位统计',
        )
