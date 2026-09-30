from django.urls import path

from apps.reservations.views import (
    AdminCancelView,
    CancelView,
    CheckInView,
    MineExportView,
    MineReservationView,
    ReservationListCreateView,
)

urlpatterns = [
    path('reservations/mine/export/', MineExportView.as_view()),
    path('reservations/mine/', MineReservationView.as_view()),
    path('reservations/', ReservationListCreateView.as_view()),
    path('reservations/<int:reservation_id>/cancel/', CancelView.as_view()),
    path('reservations/<int:reservation_id>/admin-cancel/', AdminCancelView.as_view()),
    path('reservations/<int:reservation_id>/check-in/', CheckInView.as_view()),
]
