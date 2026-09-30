import time
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone

from apps.common.config import get_configs
from apps.common.errors import BusinessError
from apps.common.utils import aware_on, fmt_dt, log_action, optional_range, parse_date
from apps.facecore.errors import FaceError, face_message
from apps.reservations.models import CheckIn, Reservation
from apps.rooms.models import RoomSlot, Seat
from apps.rooms.services import STATUS_LABELS, slot_dict

ACTIVE = ('pending', 'checked_in')
COLORS = {
    'free': '#22c55e',
    'reserved': '#f59e0b',
    'occupied': '#ef4444',
    'unavailable': '#9ca3af',
}
STATUS_TEXT = {
    'free': '空闲',
    'reserved': '预约中',
    'occupied': '占用',
    'unavailable': '不可用',
}
RES_LABELS = {
    'pending': '预约中',
    'checked_in': '已签到',
    'completed': '已完成',
    'cancelled': '已取消',
    'expired': '爽约',
    'admin_cancelled': '管理员取消',
}
RULE_KEYS = (
    'booking_days',
    'booking_cutoff_minutes',
    'checkin_early_minutes',
    'checkin_late_minutes',
    'face_threshold',
)


def reservation_queryset():
    return Reservation.objects.select_related('room', 'seat', 'slot', 'user').prefetch_related('check_ins')


def filter_reservations(queryset, request):
    start, end = optional_range(request)
    if start:
        queryset = queryset.filter(reserve_date__gte=start)
    if end:
        queryset = queryset.filter(reserve_date__lte=end)
    status = request.query_params.get('status')
    if status:
        if status not in RES_LABELS:
            raise BusinessError('状态不正确')
        queryset = queryset.filter(status=status)
    room_id = request.query_params.get('room_id')
    if room_id:
        try:
            queryset = queryset.filter(room_id=int(room_id))
        except (TypeError, ValueError):
            raise BusinessError('自习室不正确')
    return queryset.order_by('-reserve_date', '-start_at', '-id')


def reservation_to_dict(reservation, viewer, cfg=None):
    if cfg is None:
        cfg = get_configs(('checkin_early_minutes', 'checkin_late_minutes'))
    now = timezone.now()
    late = reservation.start_at + timedelta(minutes=cfg['checkin_late_minutes'])
    checks = list(reservation.check_ins.all())
    passed = next((item for item in checks if item.result == 'pass'), None)
    if passed:
        result_label = '通过'
        checkin_at = fmt_dt(passed.created_at)
    elif checks:
        result_label = '未通过'
        checkin_at = ''
    else:
        result_label = '未签到'
        checkin_at = ''
    data = {
        'id': reservation.id,
        'room_id': reservation.room_id,
        'room_name': reservation.room.name,
        'seat_id': reservation.seat_id,
        'seat_code': reservation.seat.code,
        'zone': reservation.seat.zone,
        'slot_id': reservation.slot_id,
        'slot_name': reservation.slot.name,
        'reserve_date': reservation.reserve_date.isoformat(),
        'start_time': reservation.slot.start_time.strftime('%H:%M'),
        'end_time': reservation.slot.end_time.strftime('%H:%M'),
        'start_at': fmt_dt(reservation.start_at),
        'end_at': fmt_dt(reservation.end_at),
        'status': reservation.status,
        'status_label': RES_LABELS.get(reservation.status, reservation.status),
        'cancel_reason': reservation.cancel_reason,
        'created_at': fmt_dt(reservation.created_at),
        'checkin_result': result_label,
        'checkin_at': checkin_at,
        'can_cancel': (
            viewer.role == 'student'
            and reservation.user_id == viewer.id
            and reservation.status == 'pending'
            and now < reservation.start_at
        ),
        'can_check_in': (
            reservation.user_id == viewer.id
            and reservation.status == 'pending'
            and now <= late
        ),
    }
    if viewer.role == 'admin':
        data.update({
            'user_id': reservation.user_id,
            'username': reservation.user.username,
            'nickname': reservation.user.nickname,
            'student_no': reservation.user.student_no or '',
        })
    return data


def _visible(reservation, viewer):
    if reservation is None:
        return None, False
    owner = reservation.user_id == viewer.id
    if viewer.role == 'admin' or owner:
        return reservation.id, owner
    return None, False


def _state(status, can_book, book_tip, reservation, viewer):
    reservation_id, is_mine = _visible(reservation, viewer)
    return {
        'status': status,
        'status_label': STATUS_TEXT[status],
        'color': COLORS[status],
        'can_book': can_book,
        'book_tip': book_tip,
        'reservation_id': reservation_id,
        'is_mine': is_mine,
    }


def resolve_seat(seat, room, slot, day, reservation, viewer, now, cfg):
    start_at = aware_on(day, slot.start_time)
    end_at = aware_on(day, slot.end_time)
    today = timezone.localdate()
    last_day = today + timedelta(days=cfg['booking_days'] - 1)
    late_at = start_at + timedelta(minutes=cfg['checkin_late_minutes'])
    cutoff_at = start_at - timedelta(minutes=cfg['booking_cutoff_minutes'])

    if reservation and reservation.status == 'pending' and now > late_at:
        return _state('unavailable', False, '该时段预约已失效', reservation, viewer)
    if reservation and reservation.status == 'checked_in' and now < end_at:
        return _state('occupied', False, '', reservation, viewer)

    active = reservation
    if reservation and reservation.status == 'checked_in' and now >= end_at:
        active = None
    if active and active.status == 'pending':
        return _state('reserved', False, '', active, viewer)

    structural_ok = room.status == 'open' and seat.enabled and slot.enabled
    in_window = today <= day <= last_day
    if not structural_ok or not in_window:
        return _state('unavailable', False, '当前不可预约', None, viewer)
    if now > cutoff_at:
        return _state('free', False, '已超过预约截止时间', None, viewer)
    if viewer.role != 'student':
        return _state('free', False, '仅学生可以预约', None, viewer)
    return _state('free', True, '', None, viewer)


def _load_active(seats, day, slot):
    rows = Reservation.objects.filter(
        seat__in=seats,
        reserve_date=day,
        slot=slot,
        status__in=ACTIVE,
    ).select_related('user')
    return {item.seat_id: item for item in rows}


def seat_board(room, date_text, slot_id, viewer):
    day = parse_date(date_text)
    slot = RoomSlot.objects.filter(pk=slot_id, room=room).first()
    if slot is None:
        raise BusinessError('时段不正确')
    cfg = get_configs(RULE_KEYS)
    now = timezone.now()
    seats = list(room.seats.all())
    occupied = _load_active(seats, day, slot)
    payload = []
    for seat in seats:
        state = resolve_seat(seat, room, slot, day, occupied.get(seat.id), viewer, now, cfg)
        payload.append({
            'id': seat.id,
            'code': seat.code,
            'zone': seat.zone,
            'row_no': seat.row_no,
            'col_no': seat.col_no,
            'enabled': seat.enabled,
            **state,
        })
    return {
        'room': {
            'id': room.id,
            'name': room.name,
            'status': room.status,
            'status_label': STATUS_LABELS.get(room.status, room.status),
        },
        'slot': slot_dict(slot),
        'seats': payload,
    }


def seat_detail(seat, date_text, slot_id, viewer):
    day = parse_date(date_text)
    slot = RoomSlot.objects.filter(pk=slot_id, room=seat.room).first()
    if slot is None:
        raise BusinessError('时段不正确')
    cfg = get_configs(RULE_KEYS)
    reservation = Reservation.objects.select_related('user').filter(
        seat=seat,
        reserve_date=day,
        slot=slot,
        status__in=ACTIVE,
    ).first()
    state = resolve_seat(seat, seat.room, slot, day, reservation, viewer, timezone.now(), cfg)
    detail = {
        'id': seat.id,
        'code': seat.code,
        'zone': seat.zone,
        'row_no': seat.row_no,
        'col_no': seat.col_no,
        'room_id': seat.room_id,
        'room_name': seat.room.name,
        **state,
        'reservation': None,
    }
    if reservation and state['reservation_id']:
        detail['reservation'] = {
            'id': reservation.id,
            'status': reservation.status,
            'status_label': RES_LABELS.get(reservation.status, reservation.status),
            'is_mine': reservation.user_id == viewer.id,
            'user_nickname': reservation.user.nickname,
            'user_student_no': reservation.user.student_no or '',
        }
    return detail


def create_reservation(user, seat_id, slot_id, reserve_date):
    if user.role != 'student':
        raise BusinessError('只有学生可以预约', 403)
    day = reserve_date if hasattr(reserve_date, 'year') else parse_date(str(reserve_date))
    seat = Seat.objects.select_related('room').filter(pk=seat_id).first()
    if seat is None:
        raise BusinessError('座位不存在', 404)
    slot = RoomSlot.objects.filter(pk=slot_id, room=seat.room).first()
    if slot is None:
        raise BusinessError('时段不正确')
    cfg = get_configs(('booking_days', 'booking_cutoff_minutes'))
    today = timezone.localdate()
    last_day = today + timedelta(days=cfg['booking_days'] - 1)
    if day < today or day > last_day:
        raise BusinessError('不在可预约日期范围内')
    if seat.room.status != 'open' or not seat.enabled or not slot.enabled:
        raise BusinessError('该座位当前不可预约')
    start_at = aware_on(day, slot.start_time)
    end_at = aware_on(day, slot.end_time)
    if timezone.now() > start_at - timedelta(minutes=cfg['booking_cutoff_minutes']):
        raise BusinessError('已超过预约截止时间')
    reservation = None
    lock_error = None
    for attempt in range(5):
        try:
            with transaction.atomic():
                if Reservation.objects.filter(
                    user=user,
                    status__in=ACTIVE,
                    start_at__lt=end_at,
                    end_at__gt=start_at,
                ).exists():
                    raise BusinessError('该时段已有其他预约')
                try:
                    with transaction.atomic():
                        reservation = Reservation.objects.create(
                            user=user,
                            room=seat.room,
                            seat=seat,
                            slot=slot,
                            reserve_date=day,
                            start_at=start_at,
                            end_at=end_at,
                            status=Reservation.Status.PENDING,
                        )
                except IntegrityError as exc:
                    raise BusinessError('该座位已被预约', 409) from exc
                if Reservation.objects.filter(
                    user=user,
                    status__in=ACTIVE,
                    start_at__lt=end_at,
                    end_at__gt=start_at,
                ).count() > 1:
                    raise BusinessError('该时段已有其他预约')
            break
        except OperationalError as exc:
            reservation = None
            lock_error = exc
            time.sleep(0.05 * (attempt + 1))
    if reservation is None:
        raise BusinessError('预约拥挤，请稍后重试', 409) from lock_error
    reservation = reservation_queryset().get(pk=reservation.id)
    return reservation_to_dict(reservation, user)


def cancel_reservation(user, reservation_id):
    reservation = reservation_queryset().filter(pk=reservation_id, user=user).first()
    if reservation is None:
        raise BusinessError('预约不存在', 404)
    if reservation.status != Reservation.Status.PENDING:
        raise BusinessError('当前状态不可取消')
    if timezone.now() >= reservation.start_at:
        raise BusinessError('开始后不能取消')
    reservation.status = Reservation.Status.CANCELLED
    reservation.save(update_fields=['status', 'updated_at'])
    return reservation_to_dict(reservation, user)


def admin_cancel(admin, reservation_id, reason):
    text = str(reason or '').strip()
    if not text:
        raise BusinessError('请填写取消原因')
    reservation = reservation_queryset().filter(pk=reservation_id).first()
    if reservation is None:
        raise BusinessError('预约不存在', 404)
    if reservation.status not in ACTIVE:
        raise BusinessError('当前状态不可取消')
    reservation.status = Reservation.Status.ADMIN_CANCELLED
    reservation.cancel_reason = text[:255]
    reservation.save(update_fields=['status', 'cancel_reason', 'updated_at'])
    log_action(admin, 'admin_cancel', 'reservation', reservation.id, text)
    return reservation_to_dict(reservation, admin)


def cancel_future_pending(queryset, reason, admin, action):
    now = timezone.now()
    rows = list(queryset.filter(status=Reservation.Status.PENDING, start_at__gt=now))
    for row in rows:
        row.status = Reservation.Status.ADMIN_CANCELLED
        row.cancel_reason = reason[:255]
        row.save(update_fields=['status', 'cancel_reason', 'updated_at'])
    if rows and admin is not None:
        log_action(admin, action, 'reservation', rows[0].id, f'{reason}，共 {len(rows)} 条')
    return len(rows)


def save_checkin_image(image_bytes, reservation_id):
    if not image_bytes:
        return ''
    try:
        from PIL import Image
        image = Image.open(BytesIO(image_bytes))
        image = image.convert('RGB')
        image.thumbnail((1280, 1280))
    except Exception:
        return ''
    day = timezone.localdate().strftime('%Y%m%d')
    folder = Path(settings.MEDIA_ROOT) / 'checkins' / day
    folder.mkdir(parents=True, exist_ok=True)
    name = f'{reservation_id}_{timezone.now().strftime("%H%M%S%f")}.jpg'
    image.save(folder / name, format='JPEG', quality=85)
    return f'checkins/{day}/{name}'


def _reject(reservation, user, score, reason, image):
    CheckIn.objects.create(
        reservation=reservation,
        user=user,
        score=score,
        result=CheckIn.Result.REJECT,
        fail_reason=(reason or '')[:64],
        image=image or '',
    )


def check_in(user, reservation_id, image_bytes):
    from apps.facecore.service import compare, extract_embedding

    reservation = reservation_queryset().filter(pk=reservation_id, user=user).first()
    if reservation is None:
        raise BusinessError('预约不存在', 404)
    if reservation.status != Reservation.Status.PENDING:
        raise BusinessError('当前状态不可签到')
    cfg = get_configs(('checkin_late_minutes', 'face_threshold'))
    now = timezone.now()
    late = reservation.start_at + timedelta(minutes=cfg['checkin_late_minutes'])
    if now > late:
        _reject(reservation, user, 0, '不在签到时间窗口内', '')
        raise BusinessError('不在签到时间窗口内')
    if not image_bytes:
        _reject(reservation, user, 0, '未上传照片', '')
        raise BusinessError('请上传照片')
    if len(image_bytes) > 2 * 1024 * 1024:
        _reject(reservation, user, 0, '图片过大', '')
        raise BusinessError('图片不能超过 2MB')
    image_path = save_checkin_image(image_bytes, reservation.id)
    profile = getattr(user, 'face_profile', None) if user.face_enrolled else None
    enrolled = profile.vector() if profile else None
    if not enrolled:
        _reject(reservation, user, 0, '尚未采集人脸', image_path)
        raise BusinessError('请先完成人脸采集')
    try:
        live = extract_embedding(image_bytes)
        score = compare(live, enrolled)
    except FaceError as exc:
        _reject(reservation, user, 0, face_message(exc.code), image_path)
        raise
    if score < cfg['face_threshold']:
        _reject(reservation, user, score, '人脸比对未通过', image_path)
        raise BusinessError('人脸比对未通过')
    try:
        with transaction.atomic():
            current = Reservation.objects.get(pk=reservation.id)
            if current.status != Reservation.Status.PENDING:
                raise BusinessError('当前状态不可签到')
            CheckIn.objects.create(
                reservation=current,
                user=user,
                score=score,
                result=CheckIn.Result.PASS,
                fail_reason='',
                image=image_path,
            )
            current.status = Reservation.Status.CHECKED_IN
            current.save(update_fields=['status', 'updated_at'])
    except IntegrityError as exc:
        raise BusinessError('该预约已签到') from exc
    current = reservation_queryset().get(pk=reservation.id)
    payload = reservation_to_dict(current, user, cfg)
    payload['passed'] = True
    payload['seat_code'] = current.seat.code
    payload['slot_label'] = f"{payload['start_time']}-{payload['end_time']}"
    return payload


def cleanup_checkin_images():
    deadline = timezone.now() - timedelta(days=7)
    removed = 0
    rows = CheckIn.objects.filter(created_at__lt=deadline).exclude(image='')
    for row in rows:
        path = Path(settings.MEDIA_ROOT) / row.image
        if path.exists():
            path.unlink()
        row.image = ''
        row.save(update_fields=['image'])
        removed += 1
    return removed


def sweep():
    now = timezone.now()
    late = get_configs(('checkin_late_minutes',))['checkin_late_minutes']
    expired = Reservation.objects.filter(
        status=Reservation.Status.PENDING,
        start_at__lt=now - timedelta(minutes=late),
    ).update(status=Reservation.Status.EXPIRED, updated_at=now)
    completed = Reservation.objects.filter(
        status=Reservation.Status.CHECKED_IN,
        end_at__lte=now,
    ).update(status=Reservation.Status.COMPLETED, updated_at=now)
    removed = cleanup_checkin_images()
    return {'expired': expired, 'completed': completed, 'images': removed}


def export_rows(queryset):
    rows = []
    for item in queryset:
        data = reservation_to_dict(item, item.user)
        rows.append([
            data['reserve_date'],
            data['room_name'],
            data['zone'],
            data['seat_code'],
            f"{data['start_time']}-{data['end_time']}",
            data['created_at'],
            data['status_label'],
            data['checkin_at'],
            data['checkin_result'],
        ])
    return rows
