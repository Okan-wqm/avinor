"""Base settings for Training Service."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR.parent.parent.parent))

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'apps.core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'shared.common.middleware.RequestIDMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'training_service_db'),
        'USER': os.environ.get('DB_USER', 'training_service_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'training_service_password'),
        'HOST': os.environ.get('DB_HOST', 'pgbouncer'),
        'PORT': os.environ.get('DB_PORT', '6432'),
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['shared.common.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'shared.common.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'shared.common.exceptions.custom_exception_handler',
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/6')
CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': REDIS_URL}}

# NATS Configuration
NATS_SERVERS = os.environ.get('NATS_SERVERS', 'nats://localhost:4222').split(',')
NATS_USER = os.environ.get('NATS_USER', None)
NATS_PASSWORD = os.environ.get('NATS_PASSWORD', None)
NATS_STREAM_NAME = os.environ.get('NATS_STREAM_NAME', 'FTMS_EVENTS')

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
SERVICE_NAME = 'training-service'
SERVICE_PORT = 8007
