"""
Django settings for MazaShield project.
"""
from dotenv import load_dotenv
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()
# =====================
# SECURITY
# =====================
print("ENV CHECK:", os.environ)

_raw_secret = os.getenv("SECRET_KEY")

if _raw_secret:
    # strip surrounding quotes if accidentally saved with quotes
    SECRET_KEY = _raw_secret.strip("\"'\n ")
else:
    SECRET_KEY = None

# Default to True to make local development easy; set DEBUG=False in production env.
DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes")

# include Railway production domain by default so deployments there are allowed unless overridden
DEFAULT_ALLOWED = "localhost,127.0.0.1,mazashield-backend-production.up.railway.app"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", DEFAULT_ALLOWED).split(",") if h.strip()]

# =====================
# REST FRAMEWORK & JWT
# =====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'
# =====================
# APPLICATIONS
# =====================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'MazaShield.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'MazaShield.wsgi.application'

# =====================
# DATABASE
# =====================
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True
    )
}

# =====================
# CORS
# =====================
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:3000'
    ).split(',') if o.strip()
]

# =====================
# PASSWORD VALIDATION
# =====================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =====================
# INTERNATIONALIZATION
# =====================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# =====================
# STATIC FILES
# =====================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =====================
# MISC
# =====================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'