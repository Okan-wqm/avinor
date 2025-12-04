# =============================================================================
# Flight Training System - Frontend Dockerfile
# Multi-stage build for production
# =============================================================================

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build all apps
RUN npm run build:all

# Stage 2: Production - Nginx
FROM nginx:alpine AS production

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/default.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist/apps/shell /usr/share/nginx/html/shell
COPY --from=builder /app/dist/apps/operations /usr/share/nginx/html/mfe/operations
COPY --from=builder /app/dist/apps/training /usr/share/nginx/html/mfe/training
COPY --from=builder /app/dist/apps/admin /usr/share/nginx/html/mfe/admin

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
