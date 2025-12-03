"""
Development settings for Organization Service.
"""
from .base import *

DEBUG = True

# Development-specific settings
ALLOWED_HOSTS = ['*']

# Enable browsable API in development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]
