from django.urls import path

from apps.users.views import MeView, PasswordView, ResetPasswordView, UserListView, UserStatusView

urlpatterns = [
    path('me/password/', PasswordView.as_view()),
    path('me/', MeView.as_view()),
    path('', UserListView.as_view()),
    path('<int:user_id>/status/', UserStatusView.as_view()),
    path('<int:user_id>/reset-password/', ResetPasswordView.as_view()),
]
