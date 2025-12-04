# services/api-gateway/docker/Dockerfile
# Custom Kong image with FlightSchool plugins

FROM kong:3.5

# Set environment
ENV KONG_PLUGINS=bundled,flightschool-auth
ENV KONG_LUA_PACKAGE_PATH=/opt/kong/plugins/?.lua;;

# Copy custom plugins
COPY plugins/ /opt/kong/plugins/

# Copy Kong configuration
COPY kong/kong.yml /opt/kong/kong.yml

# Set permissions
USER root
RUN chown -R kong:kong /opt/kong/plugins
USER kong

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD kong health || exit 1

EXPOSE 8000 8443 8001 8444
