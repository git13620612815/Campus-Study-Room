from django.contrib import admin

from apps.rooms.models import RoomSlot, Seat, StudyRoom


class RoomSlotInline(admin.TabularInline):
    model = RoomSlot
    extra = 0


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0


@admin.register(StudyRoom)
class StudyRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'building', 'floor', 'status')
    inlines = [RoomSlotInline, SeatInline]
