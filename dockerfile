# Use official Python image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies (pymediainfo requires mediainfo)
RUN apt-get update && \
    apt-get install -y --no-install-recommends mediainfo curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY taggarr/ ./taggarr/
COPY main.py ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Default environment variables (override in docker-compose)
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

# Entrypoint
CMD ["uv", "run", "taggarr", "--loop"]
