import re
from datetime import datetime

from django.db import transaction
from django.db.models import Count, Q

from apps.common.errors import BusinessError
from apps.common.utils import aware_on, log_action
from apps.rooms.models import RoomSlot, Seat, StudyRoom

DEFAULT_SLOTS = [
    ('上午 1', '08:00', '10:00', 1),
    ('上午 2', '10:00', '12:00', 2),
    ('下午 1', '14:00', '16:00', 3),
    ('下午 2', '16:00', '18:00', 4),
    ('晚上', '19:00', '21:00', 5),
]
STATUS_LABELS = {
    'open': '开放',
    'closed': '关闭',
    'maintenance': '维护中',
}
PREFIX_RE = re.compile(r'^[A-Za-z]{1,4}$')


def parse_clock(value):
    if hasattr(value, 'hour') and not isinstance(value, str):
        return value
    text = str(value).strip()
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(text, fmt).time().replace(microsecond=0)
        except ValueError:
            continue
    raise BusinessError('时间格式应为 HH:MM')


def clock_text(value):
    return value.strftime('%H:%M')


def slot_dict(slot):
    return {
        'id': slot.id,
        'name': slot.name,
        'start_time': clock_text(slot.start_time),
        'end_time': clock_text(slot.end_time),
        'enabled': slot.enabled,
        'sort_order': slot.sort_order,
    }


def room_dict(room):
    slots = list(room.slots.all())
    return {
        'id': room.id,
        'name': room.name,
        'building': room.building,
        'floor': room.floor,
        'facilities': room.facilities,
        'status': room.status,
        'status_label': STATUS_LABELS.get(room.status, room.status),
        'description': room.description,
        'seat_count': getattr(room, 'seat_count', room.seats.count()),
        'enabled_seat_count': getattr(room, 'enabled_seat_count', room.seats.filter(enabled=True).count()),
        'slots': [slot_dict(slot) for slot in slots],
    }


def room_queryset():
    return StudyRoom.objects.annotate(
        seat_count=Count('seats'),
        enabled_seat_count=Count('seats', filter=Q(seats__enabled=True)),
    ).prefetch_related('slots')


def create_default_slots(room):
    RoomSlot.objects.bulk_create([
        RoomSlot(
            room=room,
            name=name,
            start_time=parse_clock(start),
            end_time=parse_clock(end),
            enabled=True,
            sort_order=order,
        )
        for name, start, end, order in DEFAULT_SLOTS
    ])


def batch_create_seats(room, items):
    if not isinstance(items, list) or not items:
        raise BusinessError('请提供座位区域')
    existing = set(room.seats.values_list('code', flat=True))
    creating = []
    for item in items:
        zone = str(item.get('zone', '')).strip()
        prefix = str(item.get('prefix', '')).strip().upper()
        try:
            rows = int(item.get('rows'))
            cols = int(item.get('cols'))
        except (TypeError, ValueError):
            raise BusinessError('行数和列数应为整数')
        if not zone or len(zone) > 32:
            raise BusinessError('请填写区域名称')
        if not PREFIX_RE.match(prefix):
            raise BusinessError('座位前缀需为 1 到 4 位字母')
        if not (1 <= rows <= 20 and 1 <= cols <= 20):
            raise BusinessError('行数和列数应在 1 到 20 之间')
        number = 0
        for row in range(1, rows + 1):
            for col in range(1, cols + 1):
                number += 1
                code = f'{prefix}-{number:02d}'
                if code in existing:
                    continue
                existing.add(code)
                creating.append(Seat(
                    room=room,
                    code=code,
                    zone=zone,
                    row_no=row,
                    col_no=col,
                    enabled=True,
                ))
    if creating:
        Seat.objects.bulk_create(creating)
    return creating


def seat_admin_dict(seat):
    return {
        'id': seat.id,
        'room_id': seat.room_id,
        'code': seat.code,
        'zone': seat.zone,
        'row_no': seat.row_no,
        'col_no': seat.col_no,
        'enabled': seat.enabled,
    }


def replace_slots(room, payload, admin):
    from apps.reservations.services import cancel_future_pending

    if not isinstance(payload, list) or not payload:
        raise BusinessError('请至少保留一个时段')
    parsed = []
    for index, item in enumerate(payload, start=1):
        name = str(item.get('name', '')).strip()
        start = parse_clock(item.get('start_time'))
        end = parse_clock(item.get('end_time'))
        if not name or len(name) > 32:
            raise BusinessError('请填写时段名称')
        if start >= end:
            raise BusinessError('结束时间必须晚于开始时间')
        enabled = item.get('enabled', True)
        if not isinstance(enabled, bool):
            raise BusinessError('时段启用状态不正确')
        parsed.append({
            'id': item.get('id'),
            'name': name,
            'start_time': start,
            'end_time': end,
            'enabled': enabled,
            'sort_order': index,
        })
    for left in range(len(parsed)):
        for right in range(left + 1, len(parsed)):
            a = parsed[left]
            b = parsed[right]
            if a['start_time'] < b['end_time'] and b['start_time'] < a['end_time']:
                raise BusinessError('时段不能重叠')
            if (a['start_time'], a['end_time']) == (b['start_time'], b['end_time']):
                raise BusinessError('存在重复时段')

    with transaction.atomic():
        existing = {slot.id: slot for slot in room.slots.all()}
        kept = []
        for item in parsed:
            slot_id = item['id']
            slot = existing.get(slot_id) if slot_id else None
            if slot is None:
                slot = RoomSlot.objects.create(
                    room=room,
                    name=item['name'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    enabled=item['enabled'],
                    sort_order=item['sort_order'],
                )
            else:
                was_enabled = slot.enabled
                time_changed = slot.start_time != item['start_time'] or slot.end_time != item['end_time']
                if time_changed and slot.reservations.filter(status__in=('pending', 'checked_in')).exists():
                    raise BusinessError('时段已有未完成预约，不能修改起止时间')
                slot.name = item['name']
                slot.start_time = item['start_time']
                slot.end_time = item['end_time']
                slot.enabled = item['enabled']
                slot.sort_order = item['sort_order']
                slot.save()
                if was_enabled and not slot.enabled:
                    cancel_future_pending(slot.reservations.all(), '时段关闭', admin, 'disable_slot')
            kept.append(slot.id)
        for slot_id, slot in existing.items():
            if slot_id in kept:
                continue
            if slot.reservations.exists():
                raise BusinessError(f'时段“{slot.name}”已有预约记录，不能删除，可以关闭此时段')
            slot.delete()
    log_action(admin, 'replace_slots', 'room', room.id, '调整可预约时段')
    room = room_queryset().get(pk=room.id)
    return room_dict(room)


def apply_room_status(room, status, admin):
    from apps.reservations.services import cancel_future_pending

    if status not in STATUS_LABELS:
        raise BusinessError('自习室状态不正确')
    previous = room.status
    room.status = status
    room.save(update_fields=['status'])
    if status in (StudyRoom.Status.CLOSED, StudyRoom.Status.MAINTENANCE) and previous != status:
        reason = '自习室维护' if status == StudyRoom.Status.MAINTENANCE else '自习室关闭'
        cancel_future_pending(room.reservations.all(), reason, admin, 'close_room')
    log_action(admin, 'set_room_status', 'room', room.id, STATUS_LABELS[status])


def update_seat(seat, payload, admin):
    from apps.reservations.services import cancel_future_pending

    if 'code' in payload:
        code = str(payload.get('code', '')).strip()
        if not code or len(code) > 16:
            raise BusinessError('座位号长度应为 1 到 16')
        if Seat.objects.filter(room=seat.room, code=code).exclude(pk=seat.id).exists():
            raise BusinessError('座位号已存在')
        seat.code = code
    if 'zone' in payload:
        zone = str(payload.get('zone', '')).strip()
        if not zone or len(zone) > 32:
            raise BusinessError('请填写区域名称')
        seat.zone = zone
    if 'row_no' in payload:
        seat.row_no = _positive(payload.get('row_no'), '行号')
    if 'col_no' in payload:
        seat.col_no = _positive(payload.get('col_no'), '列号')
    disabling = False
    if 'enabled' in payload:
        enabled = payload.get('enabled')
        if not isinstance(enabled, bool):
            raise BusinessError('启用状态不正确')
        disabling = seat.enabled and not enabled
        seat.enabled = enabled
    seat.save()
    if disabling:
        cancel_future_pending(seat.reservations.all(), '座位停用', admin, 'disable_seat')
    log_action(admin, 'update_seat', 'seat', seat.id, seat.code)
    return seat_admin_dict(seat)


def _positive(value, label):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise BusinessError(f'{label}不正确')
    if number < 1:
        raise BusinessError(f'{label}不正确')
    return number
