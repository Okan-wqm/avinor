# Flight Training Management System (FTMS)

A comprehensive, production-ready microservices-based flight training management system built with Django, Docker, and modern cloud-native technologies.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NGINX (API Gateway)                            │
│                              Port: 80/443                                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                           Microservices Layer                               │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────────┤
│ User Service │ Org Service  │Aircraft Svc  │ Booking Svc  │ Flight Service  │
│   :8001      │   :8002      │   :8003      │   :8005      │    :8006        │
├──────────────┼──────────────┼──────────────┼──────────────┼─────────────────┤
│Training Svc  │ Theory Svc   │  Cert Svc    │ Finance Svc  │ Document Svc    │
│   :8007      │   :8008      │   :8009      │   :8010      │    :8011        │
├──────────────┼──────────────┼──────────────┴──────────────┴─────────────────┤
│ Report Svc   │Notification  │            Maintenance Service                │
│   :8012      │   :8013      │                :8004                          │
└──────────────┴──────────────┴───────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                           Infrastructure Layer                              │
├─────────────────┬─────────────────┬─────────────────┬───────────────────────┤
│  PostgreSQL     │  Redis Cluster  │    RabbitMQ     │       MinIO           │
│  + PgBouncer    │   (6 nodes)     │   Event Bus     │   Object Storage      │
└─────────────────┴─────────────────┴─────────────────┴───────────────────────┘
                                  │
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                           Monitoring Stack                                  │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│     Prometheus      │      Grafana        │           Jaeger                │
│      :9090          │       :3000         │           :16686                │
└─────────────────────┴─────────────────────┴─────────────────────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| User Service | 8001 | Authentication, authorization, user management |
| Organization Service | 8002 | Flight schools, clubs, organizational hierarchy |
| Aircraft Service | 8003 | Aircraft fleet management, specifications |
| Maintenance Service | 8004 | Maintenance scheduling, tracking, MEL management |
| Booking Service | 8005 | Aircraft and instructor booking system |
| Flight Service | 8006 | Flight records, logbook management |
| Training Service | 8007 | Training programs, syllabi, progress tracking |
| Theory Service | 8008 | Ground school, exams, course materials |
| Certificate Service | 8009 | Licenses, ratings, medical certificates |
| Finance Service | 8010 | Billing, payments, financial reports |
| Document Service | 8011 | Document management, version control |
| Report Service | 8012 | Analytics, reporting, dashboards |
| Notification Service | 8013 | Email, SMS, push notifications |

## Technology Stack

### Backend
- **Framework**: Django 5.0 + Django REST Framework
- **Language**: Python 3.11
- **Task Queue**: Celery with RabbitMQ
- **Caching**: Redis Cluster

### Databases
- **Primary**: PostgreSQL 16 with streaming replication
- **Connection Pooling**: PgBouncer
- **Cache**: Redis Cluster (6 nodes)
- **Object Storage**: MinIO

### Infrastructure
- **Container Runtime**: Docker + Docker Compose
- **API Gateway**: Nginx
- **Message Broker**: RabbitMQ 3.12
- **Service Discovery**: Docker DNS

### Monitoring & Observability
- **Metrics**: Prometheus
- **Visualization**: Grafana
- **Distributed Tracing**: Jaeger
- **Logging**: JSON structured logging

## Quick Start

### Prerequisites
- Docker Desktop 4.x+
- Docker Compose 2.x+
- 16GB+ RAM recommended
- 50GB+ disk space

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd Avinor

# Copy environment file
cp .env.example .env

# Edit .env and update passwords/secrets
```

### 2. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Initialize Databases

```bash
# Run migrations for all services
docker-compose exec user-service python manage.py migrate
docker-compose exec organization-service python manage.py migrate
# ... repeat for other services

# Create superuser
docker-compose exec user-service python manage.py createsuperuser
```

### 4. Access Services

| Service | URL |
|---------|-----|
| API Gateway | http://localhost |
| User Service API | http://localhost/api/v1/users |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| RabbitMQ Management | http://localhost:15672 |
| MinIO Console | http://localhost:9001 |
| Jaeger UI | http://localhost:16686 |

## Project Structure

```
Avinor/
├── docker-compose.yml              # Main orchestration file
├── .env.example                    # Environment template
├── requirements/
│   ├── base.txt                    # Core dependencies
│   ├── development.txt             # Dev dependencies
│   └── production.txt              # Production dependencies
├── shared/
│   └── common/                     # Shared libraries
│       ├── authentication.py       # JWT authentication
│       ├── permissions.py          # RBAC permissions
│       ├── pagination.py           # Pagination classes
│       ├── exceptions.py           # Custom exceptions
│       ├── mixins.py               # Model mixins
│       ├── utils.py                # Utility functions
│       ├── middleware.py           # Custom middleware
│       ├── db_routers.py           # Database routing
│       ├── cache.py                # Redis cache client
│       ├── events.py               # Event bus
│       ├── clients.py              # Service clients
│       └── metrics.py              # Prometheus metrics
├── services/
│   ├── user-service/
│   │   ├── src/
│   │   │   ├── config/             # Django settings
│   │   │   └── apps/core/          # User app
│   │   └── docker/
│   │       └── Dockerfile
│   ├── organization-service/
│   ├── aircraft-service/
│   ├── maintenance-service/
│   ├── booking-service/
│   ├── flight-service/
│   ├── training-service/
│   ├── theory-service/
│   ├── certificate-service/
│   ├── finance-service/
│   ├── document-service/
│   ├── report-service/
│   └── notification-service/
└── infrastructure/
    ├── docker/
    │   ├── Dockerfile.base
    │   ├── Dockerfile.service
    │   └── entrypoint.sh
    ├── nginx/
    │   ├── nginx.conf
    │   └── conf.d/
    ├── postgres/
    │   ├── postgresql.conf
    │   ├── pg_hba.conf
    │   ├── init-databases.sql
    │   └── pgbouncer.ini
    ├── redis-cluster/
    │   ├── redis-node.conf
    │   └── create-cluster.sh
    ├── rabbitmq/
    │   ├── rabbitmq.conf
    │   └── definitions.json
    └── monitoring/
        └── prometheus/
            └── prometheus.yml
```

## API Documentation

### Authentication

```bash
# Login
curl -X POST http://localhost/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}

# Use token
curl http://localhost/api/v1/users/me/ \
  -H "Authorization: Bearer eyJ..."
```

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/v1/auth/*` | 10 req/s |
| `/api/v1/*` | 100 req/s |

## Development

### Running Tests

```bash
# Run all tests
docker-compose exec user-service pytest

# Run with coverage
docker-compose exec user-service pytest --cov=apps --cov-report=html

# Run specific test file
docker-compose exec user-service pytest apps/core/tests/test_views.py
```

### Code Quality

```bash
# Format code
black .
isort .

# Type checking
mypy .

# Linting
flake8 .
```

### Database Migrations

```bash
# Create migrations
docker-compose exec user-service python manage.py makemigrations

# Apply migrations
docker-compose exec user-service python manage.py migrate

# Show migration status
docker-compose exec user-service python manage.py showmigrations
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | - |
| `JWT_SECRET_KEY` | JWT signing key | - |
| `POSTGRES_PASSWORD` | PostgreSQL admin password | - |
| `REDIS_PASSWORD` | Redis password | - |
| `RABBITMQ_PASSWORD` | RabbitMQ password | - |

See `.env.example` for complete list.

### Database Configuration

Each service has its own database for isolation:

| Service | Database | Port |
|---------|----------|------|
| User Service | user_service_db | 5432 |
| Organization Service | organization_service_db | 5432 |
| Aircraft Service | aircraft_service_db | 5432 |
| ... | ... | ... |

### Redis Cluster

6-node cluster configuration:
- 3 master nodes (ports 7001-7003)
- 3 replica nodes (ports 7004-7006)

## Monitoring

### Prometheus Metrics

All services expose metrics at `/metrics`:

- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `database_query_duration_seconds` - DB query latency
- `cache_hits_total` / `cache_misses_total` - Cache statistics
- `event_published_total` / `event_consumed_total` - Event metrics

### Grafana Dashboards

Pre-configured dashboards available:
- Service Overview
- Database Performance
- Redis Cluster Status
- RabbitMQ Metrics
- Request Latency

### Health Checks

```bash
# Check service health
curl http://localhost/health

# Individual service health
curl http://localhost:8001/health/
```

## Security

### Authentication Flow

1. User submits credentials to `/api/v1/auth/login/`
2. Service validates and returns JWT tokens
3. Client includes `Authorization: Bearer <token>` header
4. Each service validates token signature and claims

### RBAC Permissions

Roles:
- `ADMIN` - Full system access
- `ORGANIZATION_ADMIN` - Organization management
- `INSTRUCTOR` - Training and flight management
- `STUDENT` - Limited access to own data
- `STAFF` - Operational access

### Security Headers

Nginx adds security headers:
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Scaling

### Horizontal Scaling

```bash
# Scale a service
docker-compose up -d --scale user-service=3

# Nginx load balances automatically with least_conn
```

### Database Scaling

- Primary for writes
- Read replicas for read-heavy queries
- PgBouncer for connection pooling

### Cache Scaling

Redis Cluster provides:
- Automatic sharding
- High availability
- Automatic failover

## Troubleshooting

### Common Issues

**Services not starting**
```bash
# Check logs
docker-compose logs user-service

# Check resource usage
docker stats
```

**Database connection errors**
```bash
# Verify PostgreSQL is ready
docker-compose exec postgres-primary pg_isready

# Check PgBouncer
docker-compose exec pgbouncer psql -p 6432 -U postgres -c "SHOW POOLS"
```

**Redis Cluster issues**
```bash
# Check cluster status
docker-compose exec redis-node-1 redis-cli -c CLUSTER INFO
```

## License

Proprietary - All rights reserved.

## Support

For issues and support, please contact the development team.
