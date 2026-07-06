# logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
from functools import wraps

# Create logs directory
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


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
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO if not debug else logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
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
