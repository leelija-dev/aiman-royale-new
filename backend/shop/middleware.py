"""Keeps the admin login and the customer login apart.

The shop and the Django admin share one domain, so with a single session cookie
signing in on one side signed you out of the other. Requests under /admin/ use
their own cookie (ADMIN_SESSION_COOKIE_NAME); everything else uses the normal one.
"""
import time

from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date


def cookie_name(request):
    return settings.ADMIN_SESSION_COOKIE_NAME if request.path.startswith('/admin') else settings.SESSION_COOKIE_NAME


class SplitSessionMiddleware(SessionMiddleware):
    def process_request(self, request):
        request.session = self.SessionStore(request.COOKIES.get(cookie_name(request)))

    def process_response(self, request, response):
        try:
            accessed, modified, empty = request.session.accessed, request.session.modified, request.session.is_empty()
        except AttributeError:
            return response
        name = cookie_name(request)
        if name in request.COOKIES and empty:
            response.delete_cookie(name, path=settings.SESSION_COOKIE_PATH, domain=settings.SESSION_COOKIE_DOMAIN, samesite=settings.SESSION_COOKIE_SAMESITE)
            need_vary = True
        else:
            need_vary = accessed
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires = http_date(time.time() + max_age)
                if response.status_code < 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SessionInterrupted('The session was deleted before the request completed.')
                    response.set_cookie(name, request.session.session_key, max_age=max_age, expires=expires,
                                        domain=settings.SESSION_COOKIE_DOMAIN, path=settings.SESSION_COOKIE_PATH,
                                        secure=settings.SESSION_COOKIE_SECURE or None, httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                                        samesite=settings.SESSION_COOKIE_SAMESITE)
                    need_vary = True
        if need_vary:
            patch_vary_headers(response, ('Cookie',))
        return response
