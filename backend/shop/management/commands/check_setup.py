"""Show which integrations this server sees as configured (no secrets are printed).

    python manage.py check_setup
    docker compose exec backend python manage.py check_setup
"""
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Show which payment, courier, sign-in and email settings are configured.'

    def handle(self, *args, **o):
        s = settings
        rows = [
            ('Site address (NEXT_PUBLIC_SITE_URL)', bool(s.PUBLIC_SITE_URL) and 'localhost' not in s.PUBLIC_SITE_URL, s.PUBLIC_SITE_URL),
            ('Online payment – Cashfree', bool(s.CASHFREE_APP_ID and s.CASHFREE_SECRET_KEY), f'mode: {s.CASHFREE_ENVIRONMENT}' + ('' if s.CASHFREE_APP_ID else ' · add CASHFREE_APP_ID + CASHFREE_SECRET_KEY')),
            ('Continue with Google', bool(s.GOOGLE_CLIENT_ID and s.GOOGLE_CLIENT_SECRET), f'add this exact Authorized redirect URI in Google Cloud: {(s.GOOGLE_REDIRECT_URI if s.GOOGLE_REDIRECT_URI_SET else s.PUBLIC_SITE_URL+"/api/auth/google/callback/").replace("http://","https://") if "localhost" not in s.PUBLIC_SITE_URL else "(set NEXT_PUBLIC_SITE_URL=https://sub.aimanroyale.com in .env)"}' + ('' if s.GOOGLE_CLIENT_ID else ' · add GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET')),
            ('Courier – Delhivery', bool(s.DELHIVERY_API_TOKEN), f'mode: {s.DELHIVERY_MODE} · pickup location: {s.DELHIVERY_PICKUP_LOCATION or "MISSING"}'),
            ('Calendly booking details', bool(s.CALENDLY_TOKEN), 'optional · CALENDLY_TOKEN'),
            ('Email sending (custom request emails)', getattr(s, 'EMAIL_HOST', 'localhost') not in ('', 'localhost') or 'ses' in s.EMAIL_BACKEND.lower(), f'host: {getattr(s, "EMAIL_HOST", "")} · add EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD'),
        ]
        for name, ok, note in rows:
            self.stdout.write(f'{"✔" if ok else "✘"}  {name:<38} {note}')
        self.stdout.write('\nWith Docker, these values come from the .env file next to compose.yaml. After editing it run:\n'
                          '  docker compose up -d --force-recreate backend worker beat frontend')
