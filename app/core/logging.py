import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configures and returns the central application logger."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))

    logger = logging.getLogger("expense_tracker")
    logger.setLevel(level)

    # Prevent duplicate handlers if re-executed
    if not logger.handlers:
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logging()
