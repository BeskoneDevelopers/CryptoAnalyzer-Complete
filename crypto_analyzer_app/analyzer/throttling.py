from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class CustomAnonRateThrottle(AnonRateThrottle):
    scope = "anon"


class CustomUserRateThrottle(UserRateThrottle):
    scope = "user"

    def allow_request(self, request, view):
        if not request.user.is_authenticated:
            return True

        if request.user.is_superuser:
            return True

        return super().allow_request(request, view)


class AdminRateThrottle(UserRateThrottle):
    scope = "admin"

    def allow_request(self, request, view):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return True

        return super().allow_request(request, view)
