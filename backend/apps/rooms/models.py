from django.db import models


class StudyRoom(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', '开放'
        CLOSED = 'closed', '关闭'
        MAINTENANCE = 'maintenance', '维护中'

    name = models.CharField(max_length=64)
    building = models.CharField(max_length=64, blank=True)
    floor = models.CharField(max_length=16, blank=True)
    facilities = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'study_rooms'
        verbose_name = '自习室'
        verbose_name_plural = '自习室'
        ordering = ['id']

    def __str__(self):
        return self.name


class RoomSlot(models.Model):
    room = models.ForeignKey(StudyRoom, on_delete=models.CASCADE, related_name='slots')
    name = models.CharField(max_length=32)
    start_time = models.TimeField()
    end_time = models.TimeField()
    enabled = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'room_slots'
        verbose_name = '可预约时段'
        verbose_name_plural = '可预约时段'
        ordering = ['sort_order', 'start_time']
        constraints = [
            models.UniqueConstraint(fields=['room', 'start_time', 'end_time'], name='uniq_room_slot_time'),
        ]

    def __str__(self):
        return f'{self.room.name} {self.name}'


class Seat(models.Model):
    room = models.ForeignKey(StudyRoom, on_delete=models.CASCADE, related_name='seats')
    code = models.CharField(max_length=16)
    zone = models.CharField(max_length=32)
    row_no = models.PositiveIntegerField(default=1)
    col_no = models.PositiveIntegerField(default=1)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'seats'
        verbose_name = '座位'
        verbose_name_plural = '座位'
        ordering = ['row_no', 'col_no', 'code']
        constraints = [
            models.UniqueConstraint(fields=['room', 'code'], name='uniq_room_seat_code'),
        ]

    def __str__(self):
        return f'{self.room.name} {self.code}'
