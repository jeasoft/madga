"""MADGA settings access with sensible defaults."""

from django.conf import settings

DEFAULTS = {
    "SITE_DOMAIN": "localhost",
    "MEDIA_UPLOAD_TO": "madga/media/",
    "DEFAULT_THEME": "essay",
    "STUDIO_URL_PREFIX": "studio",
    "API_URL_PREFIX": "api/madga/v1",
    "DEFAULT_PAGINATION": 20,
    "AUTOSAVE_INTERVAL_SECONDS": 30,
}


def get_setting(name: str, default=None):
    user = getattr(settings, "MADGA", {})
    if name in user:
        return user[name]
    if name in DEFAULTS:
        return DEFAULTS[name]
    return default
