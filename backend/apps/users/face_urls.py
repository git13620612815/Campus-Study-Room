from django.urls import path

from apps.users.views import FaceEnrollView, FaceStatusView

urlpatterns = [
    path('enroll/', FaceEnrollView.as_view()),
    path('status/', FaceStatusView.as_view()),
]
