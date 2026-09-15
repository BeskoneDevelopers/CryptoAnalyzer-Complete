from django.http import Http404
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {
                "error": "Ошибка сервера. Попробуйте позже",
                "code": "server_error",
            },
            status=500,
        )

    if isinstance(exc, ValidationError):
        error = "Ошибка валидации данных"
        code = "validation_error"

    elif isinstance(exc, MethodNotAllowed):
        request = context.get("request")
        method = request.method if request else "HTTP"

        error = f"Метод {method} не разрешён"
        code = "method_not_allowed"

    elif isinstance(exc, NotAuthenticated):
        error = "Требуется авторизация"
        code = "authentication_failed"

    elif isinstance(exc, AuthenticationFailed):
        error = str(exc)
        code = "authentication_failed"

    elif isinstance(exc, PermissionDenied):
        error = "У вас недостаточно прав"
        code = "permission_denied"

    elif isinstance(exc, NotFound | Http404):
        error = "Запрашиваемый ресурс не найден"
        code = "not_found"

    elif isinstance(exc, Throttled):
        error = "Превышен лимит запросов"
        code = "throttled"

    else:
        error = "Внутренняя ошибка сервера. Попробуйте позже."
        code = "server_error"

    response.data = {
        "error": error,
        "code": code,
    }

    return response
