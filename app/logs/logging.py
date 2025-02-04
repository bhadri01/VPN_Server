import logging
import sys
import os
from loguru import logger

# Ensure logs directory exists
LOG_DIR = "app/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)  # Creates 'logs' folder if not exists

# Remove default handlers to prevent duplicate logs
logger.remove()  # Prevent duplicate handlers before adding new ones

# Configure log format
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>"

# Console logging
logger.add(sys.stderr, format=LOG_FORMAT, level="INFO", filter=lambda record: "watchfiles" not in record["message"])

# File logging with rotation and retention
logger.add(
    LOG_FILE, 
    format=LOG_FORMAT, 
    level="INFO", 
    rotation="10 MB",  # Rotates when file reaches 10MB
    retention="7 days",  # Keeps logs for 7 days
    compression="zip",  # Compresses old logs
    enqueue=True,  # Ensures thread safety
    backtrace=True,  # Captures complete error stack traces
    diagnose=True  # Provides more debugging info
)

# Standard logging integration for libraries using the 'logging' module
class InterceptHandler(logging.Handler):
    def emit(self, record):
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log(record.levelname, record.getMessage())

# Redirect standard logging messages to Loguru
logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)

# Suppress 'watchfiles' logging explicitly
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

# Ensure logs are written
logger.complete()
