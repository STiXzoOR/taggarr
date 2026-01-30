# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (pymediainfo requires mediainfo)
RUN apt-get update && \
    apt-get install -y --no-install-recommends mediainfo && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py /app/  

# Default environment variables (override in CasaOS)
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
CMD ["python", "main.py"]

