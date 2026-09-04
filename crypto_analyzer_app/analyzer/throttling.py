from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class CustomAnonRateThrottle(AnonRateThrottle):
    scope = "anon"


class CustomUserRateThrottle(UserRateThrottle):
    scope = "user"

    def allow_request(self, request, view):
        if request.user.is_authenticated and request.user.is_staff:
            self.rate = "1000/min"
            self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"
