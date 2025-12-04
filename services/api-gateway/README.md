# API Gateway (Kong)

Kong-based API Gateway for FlightSchool microservices architecture.

## Features

- **Request Routing**: Routes requests to appropriate microservices
- **Authentication**: JWT-based authentication with custom plugin
- **Rate Limiting**: Redis-backed rate limiting per consumer/IP
- **CORS**: Cross-Origin Resource Sharing management
- **Request/Response Transformation**: Header manipulation
- **Logging & Metrics**: Prometheus metrics, structured logging
- **Health Checks**: Upstream health monitoring

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env with your settings
vim .env

# 3. Run setup script
./scripts/setup-kong.sh
```

## Manual Setup

```bash
# Create network
docker network create avinor_network

# Start database
docker-compose up -d kong-database

# Run migrations
docker-compose up kong-migration

# Start Kong
docker-compose up -d kong

# (Optional) Start Konga admin UI
docker-compose --profile dev up -d konga
```

## Endpoints

| Port | Description |
|------|-------------|
| 80   | HTTP Proxy |
| 443  | HTTPS Proxy |
| 8001 | Admin API (HTTP) |
| 8444 | Admin API (HTTPS) |
| 1337 | Konga Admin UI (dev only) |

## Service Routing

| Path | Service | Port |
|------|---------|------|
| /api/v1/users, /api/v1/auth | user-service | 8001 |
| /api/v1/organizations | organization-service | 8002 |
| /api/v1/aircraft | aircraft-service | 8003 |
| /api/v1/bookings | booking-service | 8004 |
| /api/v1/flights | flight-service | 8005 |
| /api/v1/weather | weather-service | 8006 |
| /api/v1/training | training-service | 8007 |
| /api/v1/theory | theory-service | 8008 |
| /api/v1/certificates | certificate-service | 8009 |
| /api/v1/accounts, /api/v1/invoices | finance-service | 8010 |
| /api/v1/documents | document-service | 8011 |
| /api/v1/maintenance | maintenance-service | 8012 |
| /api/v1/reports | report-service | 8013 |
| /api/v1/notifications | notification-service | 8014 |

## Custom Plugin: flightschool-auth

Located in `plugins/flightschool-auth/`, this plugin handles:

1. JWT token extraction from Authorization header
2. Token validation (expiry, issuer, claims)
3. User context propagation via headers:
   - `X-User-ID`
   - `X-Organization-ID`
   - `X-User-Email`
   - `X-User-Name`
   - `X-User-Roles`
   - `X-User-Permissions`

### Public Paths (No Auth Required)

- `/api/v1/auth/login`
- `/api/v1/auth/register`
- `/api/v1/auth/forgot-password`
- `/api/v1/auth/reset-password`
- `/health`
- `/share/*`

## Rate Limits

| Scope | Limit |
|-------|-------|
| Global | 1000/min, 10000/hour |
| Auth endpoints | 20/min, 100/hour |
| Finance service | 100/min, 1000/hour |

## Configuration

### kong.yml

Declarative configuration for:
- Services and routes
- Global plugins (CORS, rate-limiting, etc.)
- Service-specific plugins
- Upstreams (for load balancing)
- Consumers (API keys)

### Environment Variables

See `.env.example` for all available options.

## Monitoring

### Prometheus Metrics

Available at `/metrics` on the admin API:

```bash
curl http://localhost:8001/metrics
```

### Health Check

```bash
curl http://localhost:8001/status
```

## Development

### Testing Routes

```bash
# Test public endpoint
curl http://localhost/api/v1/auth/login -X POST -d '{"email":"test@test.com","password":"test"}'

# Test authenticated endpoint
curl http://localhost/api/v1/users -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### View Logs

```bash
docker-compose logs -f kong
```

### Reload Configuration

```bash
# If using DB-less mode
docker-compose restart kong

# If using DB mode
curl -X POST http://localhost:8001/config -F config=@kong/kong.yml
```

## Production Notes

1. **Remove Konga** in production (it's dev-only)
2. **Restrict Admin API** to internal network
3. **Enable SSL/TLS** with proper certificates
4. **Use secrets management** for sensitive data
5. **Set up proper logging** (ELK, Datadog, etc.)
6. **Configure backups** for Kong database
