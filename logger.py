# logger.py
import logging
import os
from functools import wraps
from logging.handlers import RotatingFileHandler

from config import LOG_DIR
from utils import redact_text

# Logs live in the per-user data directory, never next to the binary.
os.makedirs(LOG_DIR, exist_ok=True)


class RedactFilter(logging.Filter):
    """Strip URLs and the home directory from every record before it is written.

    ``app.log`` is meant to be shareable in a bug report, but a downloaded
    video's URL is watch history and the home directory carries the account
    name. Redacting at the handler means every logger in the app is covered,
    including ones added later.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact_text(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        elif isinstance(record.args, dict):
            record.args = {
                key: redact_text(value) if isinstance(value, str) else value
                for key, value in record.args.items()
            }
        return True


def setup_logging(debug: bool = False):
    """Configure logging for the application."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # File handler - rotating (10MB, 5 backups)
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'app.log'),
        maxBytes=10_000_000,
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    file_handler.addFilter(RedactFilter())
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO if not debug else logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    console_handler.addFilter(RedactFilter())
    logger.addHandler(console_handler)

    return logger


def log_function(logger=None):
    """Decorator to log function entry/exit."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            log.debug(f"Entering {func.__name__}")
            try:
                result = func(*args, **kwargs)
                log.debug(f"Exiting {func.__name__}")
                return result
            except Exception as e:
                log.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


# Setup default logger
logger = setup_logging()
