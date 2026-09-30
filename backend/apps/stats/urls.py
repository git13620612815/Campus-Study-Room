from django.urls import path

from apps.stats.views import OverviewView, SeatStatsView, StatsExportView, UserStatsView, UtilizationView

urlpatterns = [
    path('overview/', OverviewView.as_view()),
    path('seats/', SeatStatsView.as_view()),
    path('users/', UserStatsView.as_view()),
    path('utilization/', UtilizationView.as_view()),
    path('export/', StatsExportView.as_view()),
]
