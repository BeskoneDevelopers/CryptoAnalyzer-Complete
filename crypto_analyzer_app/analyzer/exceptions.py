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
        return response

    error_data = {"success": False, "error": {"code": None, "message": None, "fields": None}}

    if isinstance(exc, ValidationError):
        error_data["error"]["code"] = "validation_error"
        error_data["error"]["message"] = "Ошибка валидации данных"
        error_data["error"]["fields"] = response.data

    elif isinstance(exc, MethodNotAllowed):
        error_data["error"]["code"] = "method_not_allowed"
        error_data["error"]["message"] = f"Метод {exc.detail} не разрешён"

    elif isinstance(exc, NotAuthenticated):
        error_data["error"]["code"] = "authentication_failed"
        error_data["error"]["message"] = "Требуется авторизация"

    elif isinstance(exc, AuthenticationFailed):
        error_data["error"]["code"] = "authentication_failed"
        error_data["error"]["message"] = str(exc)

    elif isinstance(exc, PermissionDenied):
        error_data["error"]["code"] = "permission_denied"
        error_data["error"]["message"] = "У вас недостаточно прав"

    elif isinstance(exc, NotFound):
        error_data["error"]["code"] = "not_found"
        error_data["error"]["message"] = "Запрашиваемый ресурс не найден"

    elif isinstance(exc, Throttled):
        error_data["error"]["code"] = "throttled"
        error_data["error"]["message"] = "Превышен лимит запросов"

    else:
        error_data["error"]["code"] = "server_error"
        error_data["error"]["message"] = "Внутренняя ошибка сервера. Попробуйте позже."

    response.data = error_data
    return Response(error_data, status=response.status_code)
