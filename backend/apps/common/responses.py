from rest_framework.response import Response


def ok(data=None, message='ok'):
    return Response({'code': 0, 'message': message, 'data': {} if data is None else data})


def fail(message, status=400):
    return Response({'code': status, 'message': message, 'data': None}, status=status)
