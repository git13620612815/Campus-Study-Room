import json

from django.contrib.auth.models import AbstractUser, UnicodeUsernameValidator
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', '学生'
        ADMIN = 'admin', '管理员'

    username = models.CharField(
        max_length=32,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        error_messages={'unique': '用户名已存在'},
    )
    email = models.EmailField(blank=True, default='')
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT, db_index=True)
    nickname = models.CharField(max_length=32, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    student_no = models.CharField(max_length=32, unique=True, null=True, blank=True)
    face_enrolled = models.BooleanField(default=False)

    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.nickname or self.username


class FaceProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='face_profile')
    embedding = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'face_profiles'
        verbose_name = '人脸档案'
        verbose_name_plural = '人脸档案'

    def vector(self):
        try:
            data = json.loads(self.embedding)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, list) or len(data) != 512:
            return None
        return data
