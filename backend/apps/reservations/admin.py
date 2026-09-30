from django.contrib import admin

from apps.reservations.models import CheckIn, Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'room', 'seat', 'reserve_date', 'status')
    list_filter = ('status', 'reserve_date')


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'user', 'result', 'score', 'created_at')
