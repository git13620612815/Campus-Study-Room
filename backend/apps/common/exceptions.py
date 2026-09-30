from rest_framework.views import exception_handler

from apps.common.responses import fail


def stringify(detail):
    if detail is None:
        return '请求不正确'
    if isinstance(detail, dict):
        parts = []
        for key, value in detail.items():
            text = stringify(value)
            parts.append(text if key == 'detail' else f'{key}: {text}')
        return '；'.join(part for part in parts if part) or '请求不正确'
    if isinstance(detail, (list, tuple)):
        return '；'.join(stringify(item) for item in detail)
    return str(detail)


def custom_exception_handler(exc, context):
    from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, NotFound, PermissionDenied

    from apps.common.errors import BusinessError
    from apps.facecore.errors import FaceError, face_message

    if isinstance(exc, BusinessError):
        return fail(exc.message, exc.status)
    if isinstance(exc, FaceError):
        return fail(face_message(exc.code), 400)
    if isinstance(exc, AuthenticationFailed):
        text = stringify(getattr(exc, 'detail', ''))
        if '停用' in text:
            return fail('账号已停用', 403)
        return fail('未登录或登录已过期', 401)
    if isinstance(exc, NotAuthenticated):
        return fail('未登录或登录已过期', 401)
    if isinstance(exc, PermissionDenied):
        return fail('没有权限执行此操作', 403)
    if isinstance(exc, NotFound):
        return fail('资源不存在', 404)

    response = exception_handler(exc, context)
    if response is None:
        return None
    message = stringify(response.data.get('detail', response.data) if isinstance(response.data, dict) else response.data)
    if response.status_code == 403:
        message = '没有权限执行此操作'
    return fail(message or '请求不正确', response.status_code)
