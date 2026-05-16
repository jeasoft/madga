"""Django settings for the MADGA dev/test project."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-b1ppp6#u#5(ir_uou8o)#b4kgdpwanozo*&@e)(st5)2m2w+b0'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',

    # MADGA must come before allauth so its template overrides for
    # account/signup.html and account/login.html win the resolve order.
    'madga',

    'allauth',
    'allauth.account',
    'allauth.headless',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # must come AFTER session, BEFORE common
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # allauth requires AccountMiddleware, must come after AuthenticationMiddleware
    'allauth.account.middleware.AccountMiddleware',
    'madga.studio.middleware.MadgaStudioMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ROOT_URLCONF = 'testproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'madga.context_processors.current_site',
                'madga.context_processors.studio_topbar',
            ],
        },
    },
]

WSGI_APPLICATION = 'testproject.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Santo_Domingo'
USE_I18N = True
USE_TZ = True

# Languages MADGA ships translations for. Sites can extend this list.
LANGUAGES = [
    ('es', 'Español'),
    ('en', 'English'),
]
# Django auto-discovers madga/locale/ (translations ship with the wheel).
# Add a project-level dir here if testproject grows its own strings.
LOCALE_PATHS: list = []

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/studio/login/'
LOGIN_REDIRECT_URL = '/studio/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@localhost'

MADGA = {
    'SITE_DOMAIN': 'localhost',
    'DEFAULT_THEME': 'essay',
    'STUDIO_URL_PREFIX': 'studio',
    'API_URL_PREFIX': 'api/madga/v1',
}

# ---------------------------------------------------------------------------
# django-allauth (headless)
# ---------------------------------------------------------------------------
# Allauth is wired in addition to Django session auth (used by /studio/).
# The headless API is exposed under /_allauth/ and is intended for
# JSON-only frontends (reader signup, login, password reset, MFA, etc.).
# Studio session login at /studio/login/ is kept untouched.

# Allow login by username OR email; email-as-username is supported.
ACCOUNT_LOGIN_METHODS = {'username', 'email'}

# Email is required at signup; username is optional.
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username', 'password1*', 'password2*']

# 'optional' = users can sign up without verifying email yet.
# Switch to 'mandatory' once an SMTP/EMAIL_BACKEND is configured.
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_UNIQUE_EMAIL = True

# Keep the regular (template-based) allauth URLs available too.
# Studio still owns its own session login at /studio/login/.
HEADLESS_ONLY = False

# Frontend URL templates that allauth includes in outgoing emails
# (verification, password reset, etc.). Empty for now: the dev project
# does not have a separate JS frontend wired. Add entries like:
#   'account_confirm_email': 'https://app.example.com/account/verify-email/{key}',
#   'account_reset_password_from_key': 'https://app.example.com/account/password/reset/key/{key}',
# when a frontend is integrated.
HEADLESS_FRONTEND_URLS: dict[str, str] = {}
