import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path):
    """Read KEY=value lines from a .env file into the environment.

    The server keeps its secret key and domain in this file, which is never
    committed. Variables that are already set are left alone.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_list(name, default=''):
    """Split a comma-separated environment variable into a clean list."""
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


load_env_file(BASE_DIR / '.env')

# Vercel sets VERCEL=1 in every deployment. When running there, default to
# production-safe values so a missing environment variable can't switch on
# debug mode or reject every request.
ON_VERCEL = os.environ.get('VERCEL') == '1'

# Production values come from environment variables; the fallbacks below are
# for local development only.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-fragransoul-dev-key-change-in-production')
DEBUG = os.environ.get('DJANGO_DEBUG', '0' if ON_VERCEL else '1') == '1'

ALLOWED_HOSTS = env_list(
    'DJANGO_ALLOWED_HOSTS',
    '.vercel.app,fragransoul.in,www.fragransoul.in'
    if ON_VERCEL
    else 'localhost,127.0.0.1'
)
CSRF_TRUSTED_ORIGINS = env_list(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'https://*.vercel.app' if ON_VERCEL else '',
)

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'store',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'fragransoul.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages', 'store.context_processors.storefront',
    ]},
}]
WSGI_APPLICATION = 'fragransoul.wsgi.application'

# Use a hosted database when DATABASE_URL is set (needed on Vercel, whose
# filesystem is read-only); otherwise fall back to local SQLite.
if os.environ.get('DATABASE_URL'):
    import dj_database_url

    DATABASES = {'default': dj_database_url.config(conn_max_age=600, ssl_require=not DEBUG)}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_USE_FINDERS = True
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # The host terminates HTTPS and forwards requests, marking them with this header.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Store settings. Orders whose subtotal reaches the threshold ship free;
# smaller orders are charged SHIPPING_FEE.
FREE_SHIPPING_THRESHOLD = Decimal('2000')
SHIPPING_FEE = Decimal('0')

# Online payments (UPI, net banking, cards) go through Razorpay and switch on
# when both keys are set. See store/payments.py.
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
# With no keys, a developer's machine uses a stand-in test payment page so the
# flow can be tried. It is never used on the live site, where DEBUG is off.
PAYMENTS_SANDBOX = DEBUG

# Background music. Put a track you have the right to use at
# static/audio/background.mp3 and it plays softly behind the store, starting
# BACKGROUND_MUSIC_START seconds in. With no file, a gentle built-in tone
# (made in the browser) plays instead.
BACKGROUND_MUSIC_FILE = 'audio/background.mp3'
BACKGROUND_MUSIC_START = 26
