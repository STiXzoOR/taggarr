"""Logging configuration for taggarr."""

import os
import logging
from datetime import datetime

from taggarr import __version__
from taggarr.config import LOG_LEVEL, LOG_PATH


def setup_logging():
    """Configure and return the taggarr logger."""
    os.makedirs(LOG_PATH, exist_ok=True)
    log_file = os.path.join(
        LOG_PATH,
        f"taggarr({__version__})_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logger = logging.getLogger("taggarr")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.debug(f"Log file created: {log_file}")

    return logger
