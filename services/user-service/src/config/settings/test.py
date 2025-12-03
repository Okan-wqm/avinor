# services/user-service/src/config/settings/test.py
"""
Test Settings

Django settings for running tests.
"""

from .base import *

# Test mode
DEBUG = False
TESTING = True

# Use in-memory SQLite for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable password hashers for faster tests
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

# Use local memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'rate_limit': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# JWT settings for testing
JWT_SECRET_KEY = 'test-secret-key-for-testing-only'
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_LIFETIME = 300  # 5 minutes
JWT_REFRESH_TOKEN_LIFETIME = 86400  # 1 day

# Event backend for testing
EVENT_BACKEND = 'memory'

# Disable rate limiting in tests
RATE_LIMITING_ENABLED = False

# Disable email verification requirement for most tests
REQUIRE_EMAIL_VERIFICATION = False

# Logging - minimal output during tests
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
    'loggers': {
        'django': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'apps': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
    },
}

# Security settings - relaxed for testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CORS - allow all for testing
CORS_ALLOW_ALL_ORIGINS = True
