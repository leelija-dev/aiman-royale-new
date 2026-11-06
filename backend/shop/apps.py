import os

from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = 'shop'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        ensure_media_folders()


def ensure_media_folders():
    """Create MEDIA_ROOT and every upload folder (products/, home/, collections/…) if missing,
    so image uploads never fail on a fresh server. Skipped when media is stored on S3."""
    from django.apps import apps
    from django.conf import settings
    from django.db import models
    if 'S3' in settings.STORAGES['default']['BACKEND']:
        return
    root = str(settings.MEDIA_ROOT)
    folders = {root}
    for model in apps.get_app_config('shop').get_models():
        for f in model._meta.get_fields():
            if isinstance(f, models.FileField) and isinstance(f.upload_to, str) and f.upload_to:
                folders.add(os.path.join(root, f.upload_to.split('%')[0].strip('/')))
    for d in folders:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            pass  # read-only checkout: Django still creates folders when a file is saved
