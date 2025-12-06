"""
Notification Service Constants.
"""

# Channels
CHANNEL_EMAIL = 'email'
CHANNEL_SMS = 'sms'
CHANNEL_PUSH = 'push'
CHANNEL_IN_APP = 'in_app'

# Status
STATUS_PENDING = 'pending'
STATUS_SENT = 'sent'
STATUS_DELIVERED = 'delivered'
STATUS_READ = 'read'
STATUS_FAILED = 'failed'

# Priority
PRIORITY_LOW = 'low'
PRIORITY_NORMAL = 'normal'
PRIORITY_HIGH = 'high'
PRIORITY_URGENT = 'urgent'

# Retry Settings
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60
RETRY_BACKOFF_MULTIPLIER = 2

# Rate Limits
EMAIL_RATE_LIMIT_PER_MINUTE = 100
SMS_RATE_LIMIT_PER_MINUTE = 50
PUSH_RATE_LIMIT_PER_MINUTE = 1000

# Batch Settings
MAX_BATCH_SIZE = 10000
BATCH_CHUNK_SIZE = 100

# Template Categories
CATEGORY_SYSTEM = 'system'
CATEGORY_BOOKING = 'booking'
CATEGORY_TRAINING = 'training'
CATEGORY_FLIGHT = 'flight'
CATEGORY_MAINTENANCE = 'maintenance'
CATEGORY_MARKETING = 'marketing'

# Error Messages
ERROR_TEMPLATE_NOT_FOUND = "Notification template not found"
ERROR_INVALID_CHANNEL = "Invalid notification channel"
ERROR_RECIPIENT_REQUIRED = "Recipient is required"
ERROR_DELIVERY_FAILED = "Failed to deliver notification"
