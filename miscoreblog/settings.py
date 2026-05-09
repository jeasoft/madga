"""Django settings for the miscoreblog project — first MADGA deployment.

Mirrors testproject's setup but uses its own SQLite DB so the two
projects don't fight over schema state. Run:

    DJANGO_SETTINGS_MODULE=miscoreblog.settings python manage.py migrate
    DJANGO_SETTINGS_MODULE=miscoreblog.settings python manage.py madga_seed_miscore
    DJANGO_SETTINGS_MODULE=miscoreblog.settings python manage.py runserver 0.0.0.0:9877
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-miscoreblog-dev-only-change-for-prod'
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

    'allauth',
    'allauth.account',
    'allauth.headless',

    'madga',
    'miscoreblog',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'madga.studio.middleware.MadgaStudioMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ROOT_URLCONF = 'miscoreblog.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'miscoreblog' / 'templates'],
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

WSGI_APPLICATION = 'miscoreblog.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'miscoreblog.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-do'
TIME_ZONE = 'America/Santo_Domingo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'miscoreblog_staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'miscoreblog' / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'miscoreblog_media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/studio/login/'
LOGIN_REDIRECT_URL = '/studio/'

MADGA = {
    'SITE_DOMAIN': 'miscore.app',
    'DEFAULT_THEME': 'miscore',
    'STUDIO_URL_PREFIX': 'studio',
    'API_URL_PREFIX': 'api/madga/v1',
}

# allauth
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_UNIQUE_EMAIL = True
HEADLESS_ONLY = False
HEADLESS_FRONTEND_URLS: dict[str, str] = {}
