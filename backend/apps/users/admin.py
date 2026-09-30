from django.contrib import admin

from apps.users.models import FaceProfile, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'nickname', 'role', 'student_no', 'phone', 'is_active', 'face_enrolled')
    list_filter = ('role', 'is_active', 'face_enrolled')
    search_fields = ('username', 'nickname', 'student_no', 'phone')


@admin.register(FaceProfile)
class FaceProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
