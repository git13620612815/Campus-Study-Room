from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class ActiveUserJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user = super().get_user(validated_token)
        except AuthenticationFailed as exc:
            text = str(getattr(exc, 'detail', exc)).lower()
            if 'inactive' in text or '停用' in text:
                raise AuthenticationFailed('账号已停用') from exc
            raise
        if not user.is_active:
            raise AuthenticationFailed('账号已停用')
        return user
