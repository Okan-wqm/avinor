# services/user-service/src/config/settings/development.py
"""
Development settings for User Service
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# Development database (can use SQLite for simplicity)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'user_db'),
        'USER': os.environ.get('DB_USER', 'user_service'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'user_service_password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# CORS - Allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Debug toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
INTERNAL_IPS = ['127.0.0.1']

# Simplified logging
LOGGING['handlers']['console']['formatter'] = 'standard'
LOGGING['root']['level'] = 'DEBUG'

# Disable throttling in development
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
