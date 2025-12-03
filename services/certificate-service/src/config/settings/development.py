# services/certificate-service/src/config/settings/development.py
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
INTERNAL_IPS = ['127.0.0.1']
LOGGING['handlers']['console']['formatter'] = 'standard'
LOGGING['root']['level'] = 'DEBUG'
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
