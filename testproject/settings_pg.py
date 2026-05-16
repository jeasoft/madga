"""Test settings — same as default but using Postgres.

Used by `madga` CI / local verification to confirm migrations and queries
work on Postgres, not just sqlite.

Spin up a throwaway Postgres:
    docker run -d --rm --name madga-pg-test \
        -e POSTGRES_PASSWORD=madga -e POSTGRES_USER=madga \
        -e POSTGRES_DB=madga_test -p 55432:5432 postgres:16-alpine

Then::
    DJANGO_SETTINGS_MODULE=testproject.settings_pg pytest tests/
"""

from testproject.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "madga_test",
        "USER": "madga",
        "PASSWORD": "madga",
        "HOST": "localhost",
        "PORT": "55432",
    }
}
