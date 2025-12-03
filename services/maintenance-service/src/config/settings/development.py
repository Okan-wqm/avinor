# services/maintenance-service/src/config/settings/development.py
"""
Development settings for Maintenance Service
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

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
