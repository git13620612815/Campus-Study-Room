from rest_framework.views import APIView

from apps.common.excel import workbook_response
from apps.common.responses import ok
from apps.common.utils import paginate
from apps.reservations.services import (
    admin_cancel,
    cancel_reservation,
    check_in,
    create_reservation,
    filter_reservations,
    reservation_queryset,
    reservation_to_dict,
)
from apps.common.config import get_configs
from apps.users.permissions import IsAdmin, IsStudent


class ReservationListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsStudent()]
        return [IsAdmin()]

    def get(self, request):
        queryset = filter_reservations(reservation_queryset(), request)
        total, rows = paginate(queryset, request)
        cfg = get_configs(('checkin_early_minutes', 'checkin_late_minutes'))
        return ok({
            'count': total,
            'results': [reservation_to_dict(item, request.user, cfg) for item in rows],
        })

    def post(self, request):
        payload = create_reservation(
            request.user,
            request.data.get('seat_id'),
            request.data.get('slot_id'),
            request.data.get('reserve_date'),
        )
        return ok(payload, '预约成功')


class MineReservationView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        queryset = filter_reservations(reservation_queryset().filter(user=request.user), request)
        total, rows = paginate(queryset, request)
        cfg = get_configs(('checkin_early_minutes', 'checkin_late_minutes'))
        return ok({
            'count': total,
            'results': [reservation_to_dict(item, request.user, cfg) for item in rows],
        })


class MineExportView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        from apps.common.errors import BusinessError
        from apps.reservations.services import export_rows

        queryset = filter_reservations(reservation_queryset().filter(user=request.user), request)
        if queryset.count() > 5000:
            raise BusinessError('结果过多，请缩小日期范围')
        return workbook_response(
            ['预约日期', '自习室', '区域', '座位号', '时段', '预约创建时间', '状态', '签到时间', '比对结果'],
            export_rows(queryset),
            '我的预约记录.xlsx',
            '预约记录',
        )


class CancelView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, reservation_id):
        return ok(cancel_reservation(request.user, reservation_id), '已取消')


class AdminCancelView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, reservation_id):
        return ok(admin_cancel(request.user, reservation_id, request.data.get('reason')), '已取消')


class CheckInView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, reservation_id):
        upload = request.FILES.get('image')
        image_bytes = upload.read() if upload is not None else b''
        return ok(check_in(request.user, reservation_id, image_bytes), '签到成功')
