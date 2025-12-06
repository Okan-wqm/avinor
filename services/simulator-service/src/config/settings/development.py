# services/simulator-service/src/config/settings/development.py
"""
Development settings for Simulator Service
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# Development database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'simulator_db'),
        'USER': os.environ.get('DB_USER', 'avinor'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'avinor_password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# CORS - Allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Additional dev tools
INSTALLED_APPS += [
    'django_extensions',
]

# Logging
LOGGING['loggers']['apps']['level'] = 'DEBUG'
