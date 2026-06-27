# config.py
"""
Central configuration for AI Study Assistant.

All environment variables and application settings are loaded and
validated here. Every other module imports from this file — no other
file should call os.getenv() or load_dotenv() directly.

Required .env file in the project root:
    GROQ_API_KEY=your_groq_api_key_here
    MAKE_WEBHOOK_URL=your_make_webhook_url_here
"""

import os
from dotenv import load_dotenv

# Load .env into os.environ exactly once, at import time.
# python-dotenv silently skips this if .env does not exist,
# which is fine in environments that inject variables another way
# (e.g. CI/CD pipelines, cloud platforms).
load_dotenv()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _require(name: str) -> str:
    """
    Read an environment variable and raise a clear error if it is missing.

    Using a helper keeps the validation logic in one place and produces
    a consistent, actionable error message for every required variable.
    """
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set.\n"
            f"Add it to your .env file:  {name}=your_value_here"
        )
    return value


# ---------------------------------------------------------------------------
# Required settings — app will not start without these
# ---------------------------------------------------------------------------

# Groq API key for authenticating with the LLM inference service.
GROQ_API_KEY: str = _require("GROQ_API_KEY")

# Make.com webhook URL for saving notes/summary/questions to Google Sheets.
MAKE_WEBHOOK_URL: str = _require("MAKE_WEBHOOK_URL")


# ---------------------------------------------------------------------------
# Model settings
# ---------------------------------------------------------------------------

# The Groq model used for all LLM calls.
# llama-3.3-70b-versatile is the best free-tier model available on Groq
# as of this project. Change this value here to switch models everywhere.
MODEL_NAME: str = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")


# ---------------------------------------------------------------------------
# LLM generation settings
# ---------------------------------------------------------------------------

# Maximum tokens the model may generate in a single response.
# 1024 is sufficient for summaries and question lists.
# Raise to 2048 if you find responses getting cut off.
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))

# Controls response creativity. 0.7 balances coherence with variety.
# Range: 0.0 (deterministic) → 1.0 (more creative).
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))


# ---------------------------------------------------------------------------
# Flask settings
# ---------------------------------------------------------------------------

# Port Flask listens on. Change via .env if 5000 is already in use.
FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))

# Debug mode. Set to "false" in production.
# Never expose debug mode to the public internet.
FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "true").lower() == "true"