"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# Sonarr
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
SONARR_URL = os.getenv("SONARR_URL")
ROOT_TV_PATH = os.getenv("ROOT_TV_PATH")

# Radarr
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
RADARR_URL = os.getenv("RADARR_URL")
ROOT_MOVIE_PATH = os.getenv("ROOT_MOVIE_PATH")

# Tags
TAG_DUB = os.getenv("TAG_DUB", "dub")
TAG_SEMI = os.getenv("TAG_SEMI", "semi-dub")
TAG_WRONG_DUB = os.getenv("TAG_WRONG", "wrong-dub")

# Behavior
RUN_INTERVAL_SECONDS = int(os.getenv("RUN_INTERVAL_SECONDS", 7200))
START_RUNNING = os.getenv("START_RUNNING", "true").lower() == "true"
QUICK_MODE = os.getenv("QUICK_MODE", "false").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
WRITE_MODE = int(os.getenv("WRITE_MODE", 0))
TARGET_LANGUAGES = [lang.strip().lower() for lang in os.getenv("TARGET_LANGUAGES", "en").split(",")]
TARGET_GENRE = os.getenv("TARGET_GENRE")
TARGET_GENRE_MOVIES = os.getenv("TARGET_GENRE_MOVIES")
ADD_TAG_TO_GENRE = os.getenv("ADD_TAG_TO_GENRE", "false").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_PATH = os.getenv("LOG_PATH", "/logs")

# Derived
SONARR_ENABLED = all([SONARR_API_KEY, SONARR_URL, ROOT_TV_PATH])
RADARR_ENABLED = all([RADARR_API_KEY, RADARR_URL, ROOT_MOVIE_PATH])

# JSON paths
TAGGARR_JSON_PATH = os.path.join(ROOT_TV_PATH, "taggarr.json") if ROOT_TV_PATH else None
TAGGARR_MOVIES_JSON_PATH = os.path.join(ROOT_MOVIE_PATH, "taggarr.json") if ROOT_MOVIE_PATH else None
