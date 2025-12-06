"""Base settings for Notification Service."""
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
        'NAME': os.environ.get('DB_NAME', 'notification_service_db'),
        'USER': os.environ.get('DB_USER', 'notif_service_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'notif_service_password'),
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
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'shared.common.exceptions.custom_exception_handler',
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/7')
CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': REDIS_URL}}
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes

# Celery Beat Schedule for periodic tasks
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'process-scheduled-notifications': {
        'task': 'apps.core.tasks.process_scheduled_notifications',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'retry-failed-notifications': {
        'task': 'apps.core.tasks.retry_failed_notifications',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}

# NATS Configuration
NATS_SERVERS = os.environ.get('NATS_SERVERS', 'nats://localhost:4222').split(',')
NATS_USER = os.environ.get('NATS_USER', None)
NATS_PASSWORD = os.environ.get('NATS_PASSWORD', None)
NATS_STREAM_NAME = os.environ.get('NATS_STREAM_NAME', 'FTMS_EVENTS')

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
SERVICE_NAME = 'notification-service'
SERVICE_PORT = 8013

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.example.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
