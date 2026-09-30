from apps.common.errors import BusinessError
from apps.common.responses import ok
from apps.reservations.services import seat_detail, seat_board
from apps.rooms.models import Seat, StudyRoom
from apps.rooms.services import (
    apply_room_status,
    batch_create_seats,
    create_default_slots,
    replace_slots,
    room_dict,
    room_queryset,
    seat_admin_dict,
    update_seat,
)
from apps.users.permissions import IsAdmin
from rest_framework.views import APIView


class RoomListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return super().get_permissions()

    def get(self, request):
        queryset = room_queryset()
        if request.user.role != 'admin':
            queryset = queryset.filter(status=StudyRoom.Status.OPEN)
        return ok([room_dict(room) for room in queryset])

    def post(self, request):
        name = str(request.data.get('name', '')).strip()
        if not name or len(name) > 64:
            raise BusinessError('请填写自习室名称')
        room = StudyRoom.objects.create(
            name=name,
            building=str(request.data.get('building', '')).strip()[:64],
            floor=str(request.data.get('floor', '')).strip()[:16],
            facilities=str(request.data.get('facilities', '')).strip()[:255],
            description=str(request.data.get('description', '')).strip()[:255],
            status=StudyRoom.Status.OPEN,
        )
        create_default_slots(room)
        return ok(room_dict(room_queryset().get(pk=room.id)), '自习室已创建')


class RoomDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAdmin()]
        return super().get_permissions()

    def get(self, request, room_id):
        room = room_queryset().filter(pk=room_id).first()
        if room is None:
            raise BusinessError('资源不存在', 404)
        if request.user.role != 'admin' and room.status != StudyRoom.Status.OPEN:
            raise BusinessError('资源不存在', 404)
        return ok(room_dict(room))

    def patch(self, request, room_id):
        room = StudyRoom.objects.filter(pk=room_id).first()
        if room is None:
            raise BusinessError('资源不存在', 404)
        for field, limit in (('name', 64), ('building', 64), ('floor', 16), ('facilities', 255), ('description', 255)):
            if field in request.data:
                value = str(request.data.get(field, '')).strip()
                if field == 'name' and not value:
                    raise BusinessError('请填写自习室名称')
                setattr(room, field, value[:limit])
        if 'status' in request.data:
            apply_room_status(room, request.data.get('status'), request.user)
        room.save()
        return ok(room_dict(room_queryset().get(pk=room.id)))


class RoomSlotsView(APIView):
    permission_classes = [IsAdmin]

    def put(self, request, room_id):
        room = StudyRoom.objects.filter(pk=room_id).first()
        if room is None:
            raise BusinessError('资源不存在', 404)
        slots = request.data.get('slots', request.data if isinstance(request.data, list) else None)
        return ok(replace_slots(room, slots, request.user))


class RoomSeatsView(APIView):
    def get(self, request, room_id):
        room = StudyRoom.objects.filter(pk=room_id).first()
        if room is None:
            raise BusinessError('资源不存在', 404)
        if request.user.role != 'admin' and room.status != StudyRoom.Status.OPEN:
            raise BusinessError('该自习室暂不可预约')
        date_text = request.query_params.get('date')
        slot_text = request.query_params.get('slot_id')
        if not date_text or not slot_text:
            raise BusinessError('请选择日期和时段')
        try:
            slot_id = int(slot_text)
        except (TypeError, ValueError):
            raise BusinessError('时段不正确')
        return ok(seat_board(room, date_text, slot_id, request.user))


class SeatBatchView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, room_id):
        room = StudyRoom.objects.filter(pk=room_id).first()
        if room is None:
            raise BusinessError('资源不存在', 404)
        created = batch_create_seats(room, request.data.get('items'))
        return ok({
            'created': len(created),
            'seats': [seat_admin_dict(seat) for seat in room.seats.all()],
        })


class SeatDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAdmin()]
        return super().get_permissions()

    def get(self, request, seat_id):
        seat = Seat.objects.select_related('room').filter(pk=seat_id).first()
        if seat is None:
            raise BusinessError('资源不存在', 404)
        date_text = request.query_params.get('date')
        slot_text = request.query_params.get('slot_id')
        if not date_text or not slot_text:
            raise BusinessError('请选择日期和时段')
        try:
            slot_id = int(slot_text)
        except (TypeError, ValueError):
            raise BusinessError('时段不正确')
        return ok(seat_detail(seat, date_text, slot_id, request.user))

    def patch(self, request, seat_id):
        seat = Seat.objects.select_related('room').filter(pk=seat_id).first()
        if seat is None:
            raise BusinessError('资源不存在', 404)
        return ok(update_seat(seat, request.data, request.user))
