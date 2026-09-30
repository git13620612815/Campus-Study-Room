from django.conf import settings
from django.db import models
from django.db.models import Q


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', '预约中'
        CHECKED_IN = 'checked_in', '已签到'
        COMPLETED = 'completed', '已完成'
        CANCELLED = 'cancelled', '已取消'
        EXPIRED = 'expired', '爽约'
        ADMIN_CANCELLED = 'admin_cancelled', '管理员取消'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    room = models.ForeignKey('rooms.StudyRoom', on_delete=models.PROTECT, related_name='reservations')
    seat = models.ForeignKey('rooms.Seat', on_delete=models.PROTECT, related_name='reservations')
    slot = models.ForeignKey('rooms.RoomSlot', on_delete=models.PROTECT, related_name='reservations')
    reserve_date = models.DateField(db_index=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    cancel_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reservations'
        verbose_name = '预约'
        verbose_name_plural = '预约'
        constraints = [
            models.UniqueConstraint(
                fields=['seat', 'reserve_date', 'slot'],
                condition=Q(status__in=['pending', 'checked_in']),
                name='uniq_active_seat_slot',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'reserve_date'], name='idx_res_user_date'),
            models.Index(fields=['room', 'reserve_date'], name='idx_res_room_date'),
        ]

    def __str__(self):
        return f'{self.user_id}-{self.seat_id}-{self.reserve_date}'


class CheckIn(models.Model):
    class Result(models.TextChoices):
        PASS = 'pass', '通过'
        REJECT = 'reject', '未通过'

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='check_ins')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='check_ins')
    score = models.FloatField(default=0)
    result = models.CharField(max_length=16, choices=Result.choices)
    fail_reason = models.CharField(max_length=64, blank=True)
    image = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'check_ins'
        verbose_name = '签到'
        verbose_name_plural = '签到'
        constraints = [
            models.UniqueConstraint(
                fields=['reservation'],
                condition=Q(result='pass'),
                name='uniq_pass_checkin',
            ),
        ]

    def __str__(self):
        return f'{self.reservation_id}:{self.result}'
