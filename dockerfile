# Build stage for frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Main image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies (pymediainfo requires mediainfo, curl for healthcheck)
# Install Node.js for running the frontend SSR server
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        mediainfo \
        curl \
        nodejs \
        npm \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY taggarr/ ./taggarr/
COPY main.py ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy frontend build and dependencies from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules
COPY --from=frontend-builder /app/frontend/package.json ./frontend/

# Create config and data directories
RUN mkdir -p /config /data /var/log/supervisor

# Supervisor configuration for running both services
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Default environment variables
ENV TAGGARR_DB_PATH=/config/taggarr.db
ENV TAGGARR_CONFIG_PATH=/config/taggarr.yaml

# Frontend environment
ENV VITE_API_URL=http://localhost:8080

# Legacy environment variables (for backward compatibility)
# Sonarr (TV Shows)
ENV SONARR_API_KEY=""
ENV SONARR_URL="http://192.168.0.1:8989"
ENV ROOT_TV_PATH="/tv"
ENV TARGET_GENRE=""

# Radarr (Movies)
ENV RADARR_API_KEY=""
ENV RADARR_URL="http://192.168.0.1:7878"
ENV ROOT_MOVIE_PATH="/movies"
ENV TARGET_GENRE_MOVIES=""

# Common options
ENV RUN_INTERVAL_SECONDS="7200"
ENV START_RUNNING="true"
ENV QUICK_MODE="false"
ENV DRY_RUN="false"
ENV WRITE_MODE="0"
ENV TAG_DUB="dub"
ENV TAG_SEMI="semi-dub"
ENV TAG_WRONG_DUB="wrong-dub"
ENV LOG_LEVEL="INFO"
ENV TARGET_LANGUAGES="english"
ENV ADD_TAG_TO_GENRE="false"

# Expose ports for API and frontend
EXPOSE 8080 3000

# Health check against API
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run both services with supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
