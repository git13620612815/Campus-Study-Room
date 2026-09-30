from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.config import DEFAULTS, get_config
from apps.common.models import SystemConfig
from apps.common.utils import aware_on
from apps.reservations.services import create_reservation
from apps.rooms.models import StudyRoom
from apps.rooms.services import batch_create_seats, create_default_slots
from apps.users.models import User


class Command(BaseCommand):
    help = '写入演示账号、两间自习室和一条预约'

    def handle(self, *args, **options):
        for key, value in DEFAULTS.items():
            SystemConfig.objects.get_or_create(key=key, defaults={'value': str(value)})

        admin, _ = User.objects.get_or_create(username='admin', defaults={'role': User.Role.ADMIN})
        admin.role = User.Role.ADMIN
        admin.nickname = '管理员'
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.student_no = None
        admin.set_password('admin123456')
        admin.save()

        student = self._student('student', '小明', '2024001', '13800138001')
        self._student('student2', '小红', '2024002', '13800138002')

        room_open = self._room('图书馆 A201', StudyRoom.Status.OPEN, '图书馆', '2', '插座,空调,台灯', '靠窗安静，适合长时间自习')
        self._room('实训楼 B105', StudyRoom.Status.MAINTENANCE, '实训楼', '1', '插座,白板', '设备维护中，暂不开放')

        if not student.reservations.filter(status__in=['pending', 'checked_in']).exists():
            placed = self._place(student, room_open)
            if placed:
                self.stdout.write(placed)

        self.stdout.write(self.style.SUCCESS('演示数据已就绪'))
        self.stdout.write('管理员 admin / admin123456')
        self.stdout.write('学生 student / student123456')
        self.stdout.write('学生 student2 / student123456')

    def _student(self, username, nickname, student_no, phone):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'role': User.Role.STUDENT, 'student_no': student_no},
        )
        user.role = User.Role.STUDENT
        user.nickname = nickname
        user.student_no = student_no
        user.phone = phone
        user.is_active = True
        user.set_password('student123456')
        user.save()
        return user

    def _room(self, name, status, building, floor, facilities, description):
        room, _ = StudyRoom.objects.get_or_create(
            name=name,
            defaults={
                'status': status,
                'building': building,
                'floor': floor,
                'facilities': facilities,
                'description': description,
            },
        )
        room.status = status
        room.building = building
        room.floor = floor
        room.facilities = facilities
        room.description = description
        room.save()
        if not room.slots.exists():
            create_default_slots(room)
        if not room.seats.exists():
            batch_create_seats(room, [
                {'zone': '靠窗', 'prefix': 'A', 'rows': 2, 'cols': 2},
                {'zone': '安静区', 'prefix': 'B', 'rows': 2, 'cols': 2},
                {'zone': '普通区', 'prefix': 'C', 'rows': 2, 'cols': 2},
            ])
        return room

    def _place(self, student, room):
        now = timezone.now()
        cutoff = get_config('booking_cutoff_minutes')
        days = get_config('booking_days')
        today = timezone.localdate()
        seat = room.seats.filter(enabled=True).order_by('row_no', 'col_no', 'code').first()
        if seat is None:
            return ''
        for offset in range(days):
            day = today + timedelta(days=offset)
            for slot in room.slots.filter(enabled=True).order_by('sort_order', 'start_time'):
                start = aware_on(day, slot.start_time)
                if now <= start - timedelta(minutes=cutoff):
                    reservation = create_reservation(student, seat.id, slot.id, day)
                    return (
                        f"已为{student.nickname}预约 {room.name} {seat.code} "
                        f"{reservation['reserve_date']} {reservation['slot_name']}"
                    )
        return ''
