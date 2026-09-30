from datetime import time

from apps.rooms.models import RoomSlot, Seat, StudyRoom
from apps.users.models import User


def make_user(username, role='student', **extra):
    password = extra.pop('password', 'password123')
    if role == 'student':
        extra.setdefault('student_no', username)
        extra.setdefault('nickname', username)
        extra.setdefault('phone', '13800138000')
    else:
        extra.setdefault('nickname', username)
        extra['student_no'] = None
    return User.objects.create_user(username=username, password=password, role=role, **extra)


def make_room(name='A201', seats=4, status='open'):
    room = StudyRoom.objects.create(
        name=name,
        building='图书馆',
        floor='2',
        facilities='插座,空调',
        status=status,
    )
    slot = RoomSlot.objects.create(
        room=room,
        name='下午 1',
        start_time=time(14, 0),
        end_time=time(16, 0),
        enabled=True,
        sort_order=1,
    )
    Seat.objects.bulk_create([
        Seat(room=room, code=f'A-{index:02d}', zone='靠窗', row_no=1, col_no=index, enabled=True)
        for index in range(1, seats + 1)
    ])
    return room, slot
