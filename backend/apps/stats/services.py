from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Count

from apps.common.config import get_configs
from apps.common.utils import daterange, minutes_between
from apps.reservations.models import Reservation
from apps.rooms.models import RoomSlot, Seat, StudyRoom

User = get_user_model()
VALID = {'pending', 'checked_in', 'completed', 'expired'}
USED = {'checked_in', 'completed'}
CANCELLED = {'cancelled', 'admin_cancelled'}
WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']


def _rate(numerator, denominator):
    if not denominator:
        return 0
    return round(numerator / denominator, 4)


def _enabled_counts(room):
    seats = sum(1 for seat in room.seats.all() if seat.enabled)
    slots = [slot for slot in room.slots.all() if slot.enabled]
    return seats, slots


def overview():
    from django.utils import timezone

    today = timezone.localdate()
    rooms = list(StudyRoom.objects.prefetch_related('seats', 'slots'))
    bookable = 0
    open_rooms = 0
    for room in rooms:
        if room.status != StudyRoom.Status.OPEN:
            continue
        open_rooms += 1
        seat_count, slots = _enabled_counts(room)
        bookable += seat_count * len(slots)
    reservations = Reservation.objects.filter(reserve_date=today)
    today_reservations = reservations.exclude(status__in=CANCELLED).count()
    today_checkins = reservations.filter(status__in=USED).count()
    return {
        'open_rooms': open_rooms,
        'today_reservations': today_reservations,
        'today_checkins': today_checkins,
        'today_usage_rate': _rate(today_checkins, bookable),
    }


def seat_usage(start, end, room_id=None):
    days = list(daterange(start, end))
    day_count = len(days)
    seats = Seat.objects.select_related('room').order_by('room_id', 'row_no', 'col_no', 'code')
    if room_id:
        seats = seats.filter(room_id=room_id)
    seat_list = list(seats)
    slot_minutes = {}
    room_minutes = defaultdict(int)
    for slot in RoomSlot.objects.filter(enabled=True):
        minutes = minutes_between(slot.start_time, slot.end_time)
        slot_minutes[slot.id] = minutes
        room_minutes[slot.room_id] += minutes
    grouped = defaultdict(list)
    reservations = Reservation.objects.filter(
        reserve_date__gte=start,
        reserve_date__lte=end,
        seat_id__in=[seat.id for seat in seat_list],
    ).exclude(status__in=CANCELLED).select_related('slot')
    for item in reservations:
        grouped[item.seat_id].append(item)
    items = []
    span = f'{start.isoformat()}~{end.isoformat()}'
    for seat in seat_list:
        room = seat.room
        per_day = room_minutes.get(room.id, 0) if room.status == StudyRoom.Status.OPEN and seat.enabled else 0
        available = per_day * day_count
        occupied = reserved_unused = book_count = checkin_count = expired_count = 0
        for item in grouped.get(seat.id, []):
            book_count += 1
            minutes = slot_minutes.get(item.slot_id)
            if minutes is None:
                minutes = minutes_between(item.slot.start_time, item.slot.end_time)
            if item.status in USED:
                checkin_count += 1
                occupied += minutes
            elif item.status == Reservation.Status.EXPIRED:
                expired_count += 1
                reserved_unused += minutes
            elif item.status == Reservation.Status.PENDING:
                reserved_unused += minutes
        items.append({
            'room_id': room.id,
            'room_name': room.name,
            'zone': seat.zone,
            'seat_id': seat.id,
            'code': seat.code,
            'span': span,
            'reservation_count': book_count,
            'checkin_count': checkin_count,
            'expired_count': expired_count,
            'occupied_minutes': occupied,
            'free_minutes': max(available - occupied - reserved_unused, 0),
            'reserved_minutes': reserved_unused,
        })
    return items


def _activity_label(valid, expired, rate, cfg):
    if expired >= 3:
        return '低活跃'
    if valid < cfg['inactive_min_reservations']:
        return '样本不足'
    if valid >= cfg['active_min_reservations'] and rate is not None and rate >= cfg['active_min_rate']:
        return '高活跃'
    if rate is not None and valid >= cfg['inactive_min_reservations'] and rate < cfg['inactive_max_rate']:
        return '低活跃'
    return '普通'


def user_activity(start, end):
    cfg = get_configs((
        'active_min_reservations',
        'active_min_rate',
        'inactive_min_reservations',
        'inactive_max_rate',
    ))
    buckets = defaultdict(lambda: {'valid': 0, 'cancel': 0, 'checkin': 0, 'expired': 0})
    rows = (
        Reservation.objects.filter(reserve_date__gte=start, reserve_date__lte=end, user__role='student')
        .values('user_id', 'status')
        .annotate(total=Count('id'))
    )
    for row in rows:
        bucket = buckets[row['user_id']]
        status = row['status']
        total = row['total']
        if status in CANCELLED:
            bucket['cancel'] += total
        else:
            bucket['valid'] += total
        if status in USED:
            bucket['checkin'] += total
        if status == Reservation.Status.EXPIRED:
            bucket['expired'] += total
    items = []
    for user in User.objects.filter(role='student').order_by('student_no', 'id'):
        bucket = buckets[user.id]
        rate = round(bucket['checkin'] / bucket['valid'], 4) if bucket['valid'] else None
        items.append({
            'id': user.id,
            'username': user.username,
            'student_no': user.student_no or '',
            'nickname': user.nickname,
            'valid_count': bucket['valid'],
            'cancel_count': bucket['cancel'],
            'checkin_count': bucket['checkin'],
            'expired_count': bucket['expired'],
            'checkin_rate': rate,
            'label': _activity_label(bucket['valid'], bucket['expired'], rate, cfg),
        })
    order = {'低活跃': 0, '高活跃': 1, '普通': 2, '样本不足': 3}
    items.sort(key=lambda item: (order[item['label']], item['student_no'] or ''))
    return items


def _day_totals(rooms, reservations, day):
    bookable = 0
    for room in rooms:
        if room.status != StudyRoom.Status.OPEN:
            continue
        seat_count, slots = _enabled_counts(room)
        bookable += seat_count * len(slots)
    day_rows = [item for item in reservations if item.reserve_date == day and item.status in VALID]
    used = sum(1 for item in day_rows if item.status in USED)
    return bookable, len(day_rows), used


def utilization(start, end):
    days = list(daterange(start, end))
    rooms = list(StudyRoom.objects.prefetch_related('slots', 'seats'))
    reservations = list(
        Reservation.objects.filter(reserve_date__gte=start, reserve_date__lte=end).select_related('slot')
    )
    line = []
    for day in days:
        bookable, valid, used = _day_totals(rooms, reservations, day)
        line.append({
            'date': day.isoformat(),
            'reservation_rate': _rate(valid, bookable),
            'usage_rate': _rate(used, bookable),
        })

    room_rows = []
    day_count = len(days)
    for room in rooms:
        seat_count, slots = _enabled_counts(room)
        denominator = seat_count * len(slots) * day_count if room.status == StudyRoom.Status.OPEN else 0
        related = [item for item in reservations if item.room_id == room.id and item.status in VALID]
        used = sum(1 for item in related if item.status in USED)
        room_rows.append({
            'room_id': room.id,
            'room_name': room.name,
            'reservation_rate': _rate(len(related), denominator),
            'usage_rate': _rate(used, denominator),
            'bookable': denominator,
            'valid_count': len(related),
            'used_count': used,
        })

    slot_keys = []
    seen = set()
    for room in rooms:
        for slot in room.slots.all():
            if not slot.enabled:
                continue
            key = (slot.start_time, slot.end_time)
            if key not in seen:
                seen.add(key)
                slot_keys.append(slot)
    slot_keys.sort(key=lambda item: (item.start_time, item.end_time))
    labels = [f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}" for slot in slot_keys]
    values = []
    for x_index, slot in enumerate(slot_keys):
        for y_index in range(7):
            samples = []
            for day in days:
                if day.weekday() != y_index:
                    continue
                bookable = 0
                used = 0
                for room in rooms:
                    if room.status != StudyRoom.Status.OPEN:
                        continue
                    matched = any(
                        item.enabled and item.start_time == slot.start_time and item.end_time == slot.end_time
                        for item in room.slots.all()
                    )
                    if not matched:
                        continue
                    seat_count = sum(1 for seat in room.seats.all() if seat.enabled)
                    bookable += seat_count
                    used += sum(
                        1
                        for item in reservations
                        if item.room_id == room.id
                        and item.reserve_date == day
                        and item.status in USED
                        and item.slot.start_time == slot.start_time
                        and item.slot.end_time == slot.end_time
                    )
                if bookable:
                    samples.append(used / bookable)
            average = round(sum(samples) / len(samples), 4) if samples else 0
            values.append([x_index, y_index, average])
    return {
        'line': line,
        'heatmap': {'x': labels, 'y': WEEKDAYS, 'values': values},
        'rooms': room_rows,
    }
