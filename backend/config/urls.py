from django.contrib import admin
from django.urls import include, path

admin.site.site_header = '校园自习室管理'
admin.site.site_title = '校园自习室'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.users.auth_urls')),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/face/', include('apps.users.face_urls')),
    path('api/v1/', include('apps.rooms.urls')),
    path('api/v1/', include('apps.reservations.urls')),
    path('api/v1/stats/', include('apps.stats.urls')),
]
