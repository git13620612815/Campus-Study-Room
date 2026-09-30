from django.urls import path

from apps.rooms.views import (
    RoomDetailView,
    RoomListCreateView,
    RoomSeatsView,
    RoomSlotsView,
    SeatBatchView,
    SeatDetailView,
)

urlpatterns = [
    path('rooms/', RoomListCreateView.as_view()),
    path('rooms/<int:room_id>/', RoomDetailView.as_view()),
    path('rooms/<int:room_id>/slots/', RoomSlotsView.as_view()),
    path('rooms/<int:room_id>/seats/batch/', SeatBatchView.as_view()),
    path('rooms/<int:room_id>/seats/', RoomSeatsView.as_view()),
    path('seats/<int:seat_id>/', SeatDetailView.as_view()),
]
