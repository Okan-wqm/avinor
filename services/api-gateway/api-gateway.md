# 🚪 MODÜL 15: API GATEWAY

## 1. GENEL BAKIŞ

### 1.1 Gateway Bilgileri

| Özellik | Değer |
|---------|-------|
| Teknoloji | Kong / Nginx |
| Port | 443 (HTTPS), 80 (HTTP redirect) |
| Admin Port | 8001 (internal) |
| Domain | api.flightschool.com |

### 1.2 Sorumluluklar

- Request routing
- Authentication/Authorization
- Rate limiting
- Request/Response transformation
- Load balancing
- SSL termination
- API versioning
- Logging ve monitoring
- CORS yönetimi

---

## 2. MİMARİ

### 2.1 Genel Yapı

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                   │
│   (Angular Web App, Mobile Apps, Third-party Integrations)      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LOAD BALANCER (AWS ALB)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API GATEWAY (Kong)                         │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────┐  │
│  │    Auth     │    Rate     │   Logging   │   Transform     │  │
│  │   Plugin    │   Limiter   │   Plugin    │    Plugin       │  │
│  └─────────────┴─────────────┴─────────────┴─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  User Service │     │ Flight Service│     │ Other Services│
│    :8001      │     │    :8006      │     │     :800x     │
└───────────────┘     └───────────────┘     └───────────────┘
```

---

## 3. KONG KONFIGÜRASYONU

### 3.1 kong.yml (Declarative Configuration)

```yaml
_format_version: "3.0"
_transform: true

# =============================================================================
# SERVICES
# =============================================================================
services:
  # User Service
  - name: user-service
    url: http://user-service:8001
    connect_timeout: 10000
    write_timeout: 60000
    read_timeout: 60000
    retries: 3
    routes:
      - name: user-routes
        paths:
          - /api/v1/users
          - /api/v1/auth
          - /api/v1/organizations
        strip_path: false
        preserve_host: true

  # Aircraft Service
  - name: aircraft-service
    url: http://aircraft-service:8002
    routes:
      - name: aircraft-routes
        paths:
          - /api/v1/aircraft
          - /api/v1/maintenance
        strip_path: false

  # Booking Service
  - name: booking-service
    url: http://booking-service:8005
    routes:
      - name: booking-routes
        paths:
          - /api/v1/bookings
        strip_path: false

  # Flight Service
  - name: flight-service
    url: http://flight-service:8006
    routes:
      - name: flight-routes
        paths:
          - /api/v1/flights
        strip_path: false

  # Training Service
  - name: training-service
    url: http://training-service:8007
    routes:
      - name: training-routes
        paths:
          - /api/v1/training
        strip_path: false

  # Theory Service
  - name: theory-service
    url: http://theory-service:8008
    routes:
      - name: theory-routes
        paths:
          - /api/v1/theory
        strip_path: false

  # Certificate Service
  - name: certificate-service
    url: http://certificate-service:8009
    routes:
      - name: certificate-routes
        paths:
          - /api/v1/certificates
        strip_path: false

  # Finance Service
  - name: finance-service
    url: http://finance-service:8010
    routes:
      - name: finance-routes
        paths:
          - /api/v1/finance
        strip_path: false

  # Document Service
  - name: document-service
    url: http://document-service:8011
    routes:
      - name: document-routes
        paths:
          - /api/v1/documents
        strip_path: false

  # Reporting Service
  - name: reporting-service
    url: http://reporting-service:8012
    routes:
      - name: reporting-routes
        paths:
          - /api/v1/reports
        strip_path: false

  # Notification Service
  - name: notification-service
    url: http://notification-service:8013
    routes:
      - name: notification-routes
        paths:
          - /api/v1/notifications
        strip_path: false

# =============================================================================
# PLUGINS (Global)
# =============================================================================
plugins:
  # CORS
  - name: cors
    config:
      origins:
        - "https://app.flightschool.com"
        - "https://*.flightschool.com"
        - "http://localhost:4200"  # Angular dev
      methods:
        - GET
        - POST
        - PUT
        - PATCH
        - DELETE
        - OPTIONS
      headers:
        - Accept
        - Authorization
        - Content-Type
        - X-Organization-ID
        - X-Request-ID
      exposed_headers:
        - X-Request-ID
        - X-RateLimit-Remaining
      credentials: true
      max_age: 3600

  # Rate Limiting (Global)
  - name: rate-limiting
    config:
      minute: 1000
      hour: 10000
      policy: redis
      redis_host: redis
      redis_port: 6379
      redis_database: 1
      fault_tolerant: true
      hide_client_headers: false

  # Request ID
  - name: correlation-id
    config:
      header_name: X-Request-ID
      generator: uuid
      echo_downstream: true

  # Logging
  - name: http-log
    config:
      http_endpoint: http://logging-service:8080/logs
      method: POST
      content_type: application/json
      timeout: 1000
      keepalive: 60000

  # Response Transformer (API Version Header)
  - name: response-transformer
    config:
      add:
        headers:
          - "X-API-Version:v1"
          - "X-Powered-By:FlightSchool"

# =============================================================================
# CONSUMERS & AUTH
# =============================================================================
consumers:
  - username: mobile-app
    custom_id: mobile-app-001
    keyauth_credentials:
      - key: mobile-api-key-xxx
    
  - username: third-party
    custom_id: third-party-001
    keyauth_credentials:
      - key: third-party-api-key-xxx
```

### 3.2 Service-Specific Plugins

```yaml
# =============================================================================
# SERVICE-SPECIFIC PLUGINS
# =============================================================================

# Auth Plugin (User Service - Login endpoint hariç)
plugins:
  - name: jwt
    service: user-service
    config:
      uri_param_names:
        - jwt
      cookie_names:
        - token
      claims_to_verify:
        - exp
      key_claim_name: kid
      secret_is_base64: false
      run_on_preflight: true
    route: user-routes
    # Login ve register endpoint'leri hariç
    
  - name: jwt
    service: aircraft-service
    config:
      claims_to_verify:
        - exp

  - name: jwt
    service: booking-service
    config:
      claims_to_verify:
        - exp

  - name: jwt
    service: flight-service
    config:
      claims_to_verify:
        - exp

  - name: jwt
    service: training-service
    config:
      claims_to_verify:
        - exp

  # Rate Limiting - Finance (daha sıkı)
  - name: rate-limiting
    service: finance-service
    config:
      minute: 100
      hour: 1000

  # Rate Limiting - Auth (brute force koruması)
  - name: rate-limiting
    route: auth-login
    config:
      minute: 10
      hour: 100
      
  # Request Size Limit - Documents
  - name: request-size-limiting
    service: document-service
    config:
      allowed_payload_size: 50  # MB
```

---

## 4. AUTHENTICATION FLOW

### 4.1 JWT Authentication

```python
# JWT Token Yapısı

# Header
{
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-id-001"
}

# Payload
{
    "sub": "user-uuid",
    "iss": "flightschool-auth",
    "aud": "flightschool-api",
    "exp": 1704067200,  # Expiration
    "iat": 1704063600,  # Issued at
    "nbf": 1704063600,  # Not before
    
    # Custom claims
    "org_id": "organization-uuid",
    "roles": ["student", "pilot"],
    "permissions": ["booking:create", "flight:read"],
    "email": "user@example.com",
    "name": "John Doe"
}

# Signature
RSASHA256(
    base64UrlEncode(header) + "." +
    base64UrlEncode(payload),
    privateKey
)
```

### 4.2 Auth Middleware (Kong Custom Plugin)

```lua
-- kong/plugins/flightschool-auth/handler.lua

local jwt_decoder = require "kong.plugins.jwt.jwt_parser"
local http = require "resty.http"

local FlightSchoolAuth = {
    PRIORITY = 1000,
    VERSION = "1.0.0",
}

function FlightSchoolAuth:access(conf)
    -- Public endpoints
    local public_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/health"
    }
    
    local path = kong.request.get_path()
    for _, public_path in ipairs(public_paths) do
        if path:find(public_path, 1, true) == 1 then
            return  -- Skip auth
        end
    end
    
    -- Get token
    local auth_header = kong.request.get_header("Authorization")
    if not auth_header then
        return kong.response.exit(401, {
            error = "Unauthorized",
            message = "Missing Authorization header"
        })
    end
    
    local token = auth_header:match("Bearer%s+(.+)")
    if not token then
        return kong.response.exit(401, {
            error = "Unauthorized",
            message = "Invalid Authorization header format"
        })
    end
    
    -- Decode and verify JWT
    local jwt, err = jwt_decoder:new(token)
    if err then
        return kong.response.exit(401, {
            error = "Unauthorized",
            message = "Invalid token"
        })
    end
    
    -- Check expiration
    local claims = jwt.claims
    if claims.exp and claims.exp < ngx.time() then
        return kong.response.exit(401, {
            error = "Unauthorized",
            message = "Token expired"
        })
    end
    
    -- Set headers for downstream services
    kong.service.request.set_header("X-User-ID", claims.sub)
    kong.service.request.set_header("X-Organization-ID", claims.org_id)
    kong.service.request.set_header("X-User-Roles", table.concat(claims.roles or {}, ","))
    kong.service.request.set_header("X-User-Email", claims.email or "")
    
    -- Store in context for logging
    kong.ctx.shared.user_id = claims.sub
    kong.ctx.shared.org_id = claims.org_id
end

return FlightSchoolAuth
```

---

## 5. RATE LIMITING STRATEJİSİ

### 5.1 Tier Bazlı Rate Limiting

```yaml
# Rate Limit Tiers
rate_limits:
  # Anonymous (API key olmadan)
  anonymous:
    minute: 60
    hour: 500
    day: 5000
  
  # Basic (Free tier)
  basic:
    minute: 200
    hour: 2000
    day: 20000
  
  # Professional
  professional:
    minute: 1000
    hour: 10000
    day: 100000
  
  # Enterprise
  enterprise:
    minute: 5000
    hour: 50000
    day: 500000

# Endpoint Specific
endpoint_limits:
  # Auth endpoints (brute force protection)
  "/api/v1/auth/login":
    minute: 10
    hour: 100
    
  "/api/v1/auth/forgot-password":
    minute: 5
    hour: 20
  
  # Document upload
  "/api/v1/documents":
    method: POST
    minute: 30
    hour: 200
  
  # Report generation
  "/api/v1/reports/*/execute":
    minute: 10
    hour: 100
  
  # Search endpoints
  "/api/v1/*/search":
    minute: 60
    hour: 600
```

### 5.2 Rate Limit Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1704067200
```

---

## 6. REQUEST/RESPONSE TRANSFORMATION

### 6.1 Request Transformation

```yaml
# Request Transformer Plugin
plugins:
  - name: request-transformer
    config:
      add:
        headers:
          - "X-Gateway-Version:1.0"
          - "X-Forwarded-Proto:https"
        querystring:
          - "api_version:v1"
      
      rename:
        headers:
          - "X-Custom-Auth:Authorization"
      
      remove:
        headers:
          - "X-Internal-Header"
```

### 6.2 Response Transformation

```yaml
# Response Transformer Plugin
plugins:
  - name: response-transformer
    config:
      add:
        headers:
          - "X-API-Version:v1"
          - "X-Request-ID:$(request.headers.x-request-id)"
          - "Strict-Transport-Security:max-age=31536000; includeSubDomains"
          - "X-Content-Type-Options:nosniff"
          - "X-Frame-Options:DENY"
      
      remove:
        headers:
          - "X-Powered-By"
          - "Server"
```

---

## 7. LOAD BALANCING

### 7.1 Upstream Configuration

```yaml
upstreams:
  - name: user-service-upstream
    algorithm: round-robin
    healthchecks:
      active:
        type: http
        http_path: /health
        timeout: 5
        healthy:
          interval: 10
          successes: 2
        unhealthy:
          interval: 5
          http_failures: 3
      passive:
        healthy:
          successes: 5
        unhealthy:
          http_failures: 5
    targets:
      - target: user-service-1:8001
        weight: 100
      - target: user-service-2:8001
        weight: 100

  - name: flight-service-upstream
    algorithm: least-connections
    healthchecks:
      active:
        type: http
        http_path: /health
    targets:
      - target: flight-service-1:8006
        weight: 100
      - target: flight-service-2:8006
        weight: 100
```

---

## 8. API VERSIONING

### 8.1 URL Based Versioning

```
/api/v1/users
/api/v2/users
```

### 8.2 Header Based Versioning

```yaml
plugins:
  - name: request-transformer
    config:
      add:
        headers:
          - "X-API-Version:$(request.headers.accept-version)"
```

### 8.3 Version Routing

```yaml
services:
  - name: user-service-v1
    url: http://user-service-v1:8001
    routes:
      - name: user-v1-routes
        paths:
          - /api/v1/users

  - name: user-service-v2
    url: http://user-service-v2:8001
    routes:
      - name: user-v2-routes
        paths:
          - /api/v2/users
```

---

## 9. ERROR HANDLING

### 9.1 Standart Error Response

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request parameters",
        "details": [
            {
                "field": "email",
                "message": "Invalid email format"
            }
        ],
        "request_id": "req-uuid-xxx",
        "timestamp": "2024-01-01T12:00:00Z"
    }
}
```

### 9.2 Gateway Error Codes

```yaml
error_codes:
  # 4xx Client Errors
  400: "Bad Request"
  401: "Unauthorized"
  403: "Forbidden"
  404: "Not Found"
  405: "Method Not Allowed"
  408: "Request Timeout"
  413: "Payload Too Large"
  429: "Too Many Requests"
  
  # 5xx Server Errors
  500: "Internal Server Error"
  502: "Bad Gateway"
  503: "Service Unavailable"
  504: "Gateway Timeout"
```

---

## 10. MONITORING & LOGGING

### 10.1 Prometheus Metrics

```yaml
plugins:
  - name: prometheus
    config:
      per_consumer: true
      status_code_metrics: true
      latency_metrics: true
      bandwidth_metrics: true
      upstream_health_metrics: true
```

### 10.2 Log Format

```json
{
    "timestamp": "2024-01-01T12:00:00.000Z",
    "request_id": "req-uuid-xxx",
    "client_ip": "192.168.1.1",
    "method": "POST",
    "path": "/api/v1/bookings",
    "query_string": "?date=2024-01-15",
    "status": 201,
    "latency_ms": 45,
    "upstream_latency_ms": 40,
    "user_id": "user-uuid",
    "organization_id": "org-uuid",
    "consumer": "mobile-app",
    "service": "booking-service",
    "route": "booking-routes",
    "request_size": 1024,
    "response_size": 512
}
```

---

## 11. SECURITY

### 11.1 Security Headers

```yaml
plugins:
  - name: response-transformer
    config:
      add:
        headers:
          - "Strict-Transport-Security:max-age=31536000; includeSubDomains; preload"
          - "X-Content-Type-Options:nosniff"
          - "X-Frame-Options:DENY"
          - "X-XSS-Protection:1; mode=block"
          - "Content-Security-Policy:default-src 'self'"
          - "Referrer-Policy:strict-origin-when-cross-origin"
```

### 11.2 IP Restriction (Admin endpoints)

```yaml
plugins:
  - name: ip-restriction
    route: admin-routes
    config:
      allow:
        - 10.0.0.0/8
        - 192.168.1.0/24
```

---

Bu doküman API Gateway'in tüm detaylarını içermektedir.