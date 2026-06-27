# backend/logger.py
"""
Centralised logging configuration for AI Study Assistant.

Sets up one shared logger with two handlers:
  - StreamHandler  → prints to the terminal during development
  - RotatingFileHandler → writes to logs/app.log (max 1 MB, keeps 3 backups)

Every other module imports `logger` from here.
Never call logging.basicConfig() or create a new logger elsewhere.

Usage in any module:
    from backend.logger import logger
    logger.info("Something happened.")
    logger.error("Something went wrong: %s", str(e))
"""

import logging
import os
from logging.handlers import RotatingFileHandler


# ---------------------------------------------------------------------------
# Log directory
# ---------------------------------------------------------------------------

# Create a logs/ folder in the project root if it does not exist.
# os.path.dirname(__file__) is backend/, so we go one level up.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_log_dir = os.path.join(_project_root, "logs")
os.makedirs(_log_dir, exist_ok=True)

_log_file = os.path.join(_log_dir, "app.log")


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------

# Every log line includes:
#   - timestamp          → when did this happen?
#   - level name         → INFO / WARNING / ERROR
#   - module name        → which file logged this?
#   - message            → what happened?
#
# Example output:
#   2024-11-01 14:32:05 | INFO     | summarizer      | Summary generated (312 tokens)
_FORMAT = "%(asctime)s | %(levelname)-8s | %(module)-20s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_formatter = logging.Formatter(fmt=_FORMAT, datefmt=_DATE_FORMAT)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

# Terminal handler — shows logs in the console while you run the app.
_stream_handler = logging.StreamHandler()
_stream_handler.setLevel(logging.DEBUG)
_stream_handler.setFormatter(_formatter)

# File handler — writes to logs/app.log.
# RotatingFileHandler caps the file at 1 MB and keeps 3 old copies,
# so logs never grow large enough to fill your disk.
_file_handler = RotatingFileHandler(
    filename=_log_file,
    maxBytes=1 * 1024 * 1024,  # 1 MB
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_formatter)


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

# Use a named logger ("study_assistant") rather than the root logger.
# Named loggers don't interfere with logging from third-party libraries
# (Flask, Groq SDK, etc.) that also use the root logger.
logger = logging.getLogger("study_assistant")
logger.setLevel(logging.DEBUG)

# Avoid adding duplicate handlers if this module is imported more than once
# (can happen in some reload scenarios during development).
if not logger.handlers:
    logger.addHandler(_stream_handler)
    logger.addHandler(_file_handler)

# Prevent log messages from bubbling up to the root logger,
# which would cause each message to print twice in the terminal.
logger.propagate = False


# ---------------------------------------------------------------------------
# Startup confirmation
# ---------------------------------------------------------------------------

logger.info("Logger initialised. Writing to: %s", _log_file)