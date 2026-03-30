FROM eclipse-temurin:21-jre-alpine

RUN apk add --no-cache python3 py3-pip py3-yaml wget procps \
    && pip3 install --no-cache-dir --break-system-packages Flask PyYAML

WORKDIR /app

# Copy web application
COPY web/ /app/web/

# Copy default config (entrypoint copies to volume if missing)
COPY config/ /app/config-default/

# Copy entrypoint
COPY scripts/entrypoint.sh /app/entrypoint.sh

# Create directories for runtime data
RUN mkdir -p /app/geyser /app/config

EXPOSE 19132/udp
EXPOSE 5000/tcp

ENTRYPOINT ["/app/entrypoint.sh"]
