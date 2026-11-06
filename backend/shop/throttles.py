"""API rate limits per visitor. Requests from our own Next.js server (page rendering and link
prefetching) carry X-Internal-Token and are not limited — they all come from one IP address and
would otherwise use up the limit for everyone."""
import hmac

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


def is_internal(request):
    token = request.META.get('HTTP_X_INTERNAL_TOKEN', '')
    return bool(token) and hmac.compare_digest(token, settings.INTERNAL_API_TOKEN)


class VisitorAnonThrottle(AnonRateThrottle):
    def allow_request(self, request, view):
        return is_internal(request) or super().allow_request(request, view)


class VisitorUserThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        return is_internal(request) or super().allow_request(request, view)
