"""Logging configuration for taggarr."""

import os
import logging
from datetime import datetime

from taggarr import __version__


def setup_logging(level: str = "INFO", path: str = "/logs"):
    """Configure and return the taggarr logger.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR)
        path: Directory path for log files
    """
    os.makedirs(path, exist_ok=True)
    log_file = os.path.join(
        path,
        f"taggarr({__version__})_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logger = logging.getLogger("taggarr")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.debug(f"Log file created: {log_file}")

    return logger
