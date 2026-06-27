# backend/groq_client.py
"""
Shared Groq SDK client.

Initialises one Groq client instance using credentials from config.py
and logs confirmation at startup. Import `client` and `MODEL_NAME` from
here in any module that calls the Groq API. Never instantiate Groq()
anywhere else in the project.

Exports:
    client    — authenticated groq.Groq instance
    MODEL_NAME — model string from config (e.g. "llama-3.3-70b-versatile")
"""

from groq import Groq

from config import GROQ_API_KEY, MODEL_NAME
from backend.logger import logger

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# Instantiated once at import time. The Groq SDK handles connection pooling
# internally, so this single instance is safe to share across all modules.
client = Groq(api_key=GROQ_API_KEY)

logger.info("Groq client initialised. Model: %s", MODEL_NAME)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["client", "MODEL_NAME"]