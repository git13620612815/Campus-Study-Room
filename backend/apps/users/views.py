import json
import re
import secrets

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.errors import BusinessError
from apps.common.responses import ok
from apps.common.utils import fmt_dt, log_action, paginate
from apps.facecore.service import extract_embedding
from apps.users.models import FaceProfile, User
from apps.users.permissions import IsAdmin

PHONE_RE = re.compile(r'^1[3-9]\d{9}$')
USERNAME_RE = re.compile(r'^[A-Za-z0-9_]{4,32}$')
STUDENT_NO_RE = re.compile(r'^[A-Za-z0-9]{4,32}$')


def issue_token(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'role': user.role,
        'nickname': user.nickname,
        'face_enrolled': user.face_enrolled,
    }


def user_dict(user):
    return {
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'nickname': user.nickname,
        'phone': user.phone,
        'student_no': user.student_no or '',
        'is_active': user.is_active,
        'face_enrolled': user.face_enrolled,
        'date_joined': fmt_dt(user.date_joined),
    }


def ensure_password(password, user=None):
    if not password or not isinstance(password, str):
        raise BusinessError('请填写密码')
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise BusinessError('；'.join(exc.messages))


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = str(request.data.get('username', '')).strip()
        password = request.data.get('password') or ''
        nickname = str(request.data.get('nickname', '')).strip()
        phone = str(request.data.get('phone', '')).strip()
        student_no = str(request.data.get('student_no', '')).strip()
        if not all([username, password, nickname, phone, student_no]):
            raise BusinessError('请完整填写注册信息')
        if not USERNAME_RE.match(username):
            raise BusinessError('用户名需为 4 到 32 位字母、数字或下划线')
        if not STUDENT_NO_RE.match(student_no):
            raise BusinessError('学号需为 4 到 32 位字母或数字')
        if not (1 <= len(nickname) <= 32):
            raise BusinessError('昵称长度为 1 到 32 个字符')
        if not PHONE_RE.match(phone):
            raise BusinessError('手机号格式不正确')
        if User.objects.filter(username=username).exists():
            raise BusinessError('用户名已存在')
        if User.objects.filter(student_no=student_no).exists():
            raise BusinessError('学号已存在')
        ensure_password(password)
        user = User.objects.create_user(
            username=username,
            password=password,
            role=User.Role.STUDENT,
            nickname=nickname,
            phone=phone,
            student_no=student_no,
        )
        return ok(user_dict(user), '注册成功')


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = str(request.data.get('username', '')).strip()
        password = request.data.get('password') or ''
        user = User.objects.filter(username=username).first()
        if user is None or not user.check_password(password):
            raise BusinessError('账号或密码错误', 401)
        if not user.is_active:
            raise BusinessError('账号已停用', 403)
        return ok(issue_token(user))


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return ok(serializer.validated_data)


class LogoutView(APIView):
    def post(self, request):
        return ok({'logged_out': True})


class MeView(APIView):
    def get(self, request):
        return ok(user_dict(request.user))

    def patch(self, request):
        user = request.user
        if 'nickname' in request.data:
            nickname = str(request.data.get('nickname', '')).strip()
            if not (1 <= len(nickname) <= 32):
                raise BusinessError('昵称长度为 1 到 32 个字符')
            user.nickname = nickname
        if 'phone' in request.data:
            phone = str(request.data.get('phone', '')).strip()
            if not PHONE_RE.match(phone):
                raise BusinessError('手机号格式不正确')
            user.phone = phone
        user.save(update_fields=['nickname', 'phone'])
        return ok(user_dict(user))


class PasswordView(APIView):
    def post(self, request):
        old_password = request.data.get('old_password') or ''
        new_password = request.data.get('new_password') or ''
        user = request.user
        if not user.check_password(old_password):
            raise BusinessError('原密码不正确')
        ensure_password(new_password, user)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return ok({'changed': True}, '密码已更新')


class UserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = User.objects.all().order_by('-date_joined')
        role = request.query_params.get('role')
        if role in (User.Role.STUDENT, User.Role.ADMIN):
            queryset = queryset.filter(role=role)
        keyword = request.query_params.get('keyword', '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(username__icontains=keyword)
                | Q(nickname__icontains=keyword)
                | Q(student_no__icontains=keyword)
                | Q(phone__icontains=keyword)
            )
        total, rows = paginate(queryset, request)
        return ok({'count': total, 'results': [user_dict(item) for item in rows]})


class UserStatusView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, user_id):
        target = User.objects.filter(pk=user_id).first()
        if target is None:
            raise BusinessError('资源不存在', 404)
        is_active = request.data.get('is_active')
        if not isinstance(is_active, bool):
            raise BusinessError('请提供 is_active')
        if target.id == request.user.id and not is_active:
            raise BusinessError('不能停用当前登录账号')
        target.is_active = is_active
        target.save(update_fields=['is_active'])
        if not is_active:
            from apps.reservations.services import cancel_future_pending

            cancel_future_pending(
                target.reservations.all(),
                '账号停用',
                request.user,
                'disable_user',
            )
        log_action(request.user, 'set_user_status', 'user', target.id, '启用' if is_active else '停用')
        return ok(user_dict(target))


class ResetPasswordView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        target = User.objects.filter(pk=user_id).first()
        if target is None:
            raise BusinessError('资源不存在', 404)
        alphabet = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        temporary = 'Stu' + ''.join(secrets.choice(alphabet) for _ in range(6))
        target.set_password(temporary)
        target.save(update_fields=['password'])
        log_action(request.user, 'reset_password', 'user', target.id, '重置密码')
        return ok({'temporary_password': temporary})


class FaceEnrollView(APIView):
    def post(self, request):
        upload = request.FILES.get('image')
        if upload is None:
            raise BusinessError('请上传照片')
        embedding = extract_embedding(upload.read())
        FaceProfile.objects.update_or_create(
            user=request.user,
            defaults={'embedding': json.dumps(embedding)},
        )
        request.user.face_enrolled = True
        request.user.save(update_fields=['face_enrolled'])
        profile = request.user.face_profile
        return ok({'face_enrolled': True, 'updated_at': fmt_dt(profile.updated_at)})


class FaceStatusView(APIView):
    def get(self, request):
        updated = ''
        if request.user.face_enrolled and hasattr(request.user, 'face_profile'):
            updated = fmt_dt(request.user.face_profile.updated_at)
        return ok({'face_enrolled': request.user.face_enrolled, 'updated_at': updated})
