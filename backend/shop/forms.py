from django.contrib.auth.forms import PasswordResetForm


class ShopPasswordResetForm(PasswordResetForm):
    """Also sends the reset link to accounts created with "Continue with Google" (or WhatsApp),
    which have no password yet — the link lets them set one."""

    def get_users(self, email):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        for u in U._default_manager.filter(email__iexact=email, is_active=True):
            if u.email and u.email.lower() == email.lower():
                yield u
