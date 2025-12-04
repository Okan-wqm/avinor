# services/finance-service/src/config/settings/testing.py
"""
Testing settings for Finance Service.
"""

from .base import *

# Testing mode
DEBUG = True
TESTING = True

# Use in-memory SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Celery
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Email
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Stripe (test mode)
STRIPE_SECRET_KEY = 'sk_test_fake_key_for_testing'
STRIPE_PUBLISHABLE_KEY = 'pk_test_fake_key_for_testing'
STRIPE_WEBHOOK_SECRET = 'whsec_test_fake_webhook_secret'

# Logging - minimal for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
}
