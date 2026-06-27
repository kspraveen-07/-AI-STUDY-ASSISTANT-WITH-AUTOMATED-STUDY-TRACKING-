# backend/webhook.py
"""
Make.com webhook integration.

Provides send_to_make() which reads the current session store and POSTs
notes, summary, and questions to the Make.com webhook URL defined in
config.py. Make.com then appends a row to Google Sheets.

This module never calls the Groq API — it only transmits data that has
already been generated and saved to the session store. Questions are
generated exactly once (by question_generator.py) and reused here.

JSON payload format sent to Make.com:
{
    "notes":     "<student's raw notes>",
    "summary":   "<generated summary>",
    "questions": ["question 1", "question 2", ...]
}
"""

import json

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from backend.logger import logger
from backend.session_store import get_store
from config import MAKE_WEBHOOK_URL

# Timeout in seconds for the POST request to Make.com.
# Prevents the UI from hanging indefinitely if Make.com is slow.
_REQUEST_TIMEOUT: int = 10


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def send_to_make() -> str:
    """
    POST the current session data to the Make.com webhook.

    Reads notes, summary, and questions from the session store and sends
    them as a JSON payload to Make.com. Make.com maps the fields to
    Google Sheets columns and appends a new row.

    Returns:
        A user-friendly status string indicating success or failure.
        The string is displayed directly in the Gradio UI status box.

    Raises:
        Does not raise — all exceptions are caught and returned as
        descriptive strings so the UI always receives a displayable value.
    """
    # ---- Read session data -------------------------------------------------
    store = get_store()

    # Validate that there is something worth sending.
    if not store["notes"]:
        logger.warning("send_to_make called with no notes in session store.")
        return "Nothing to save. Please paste your notes first."

    if not store["summary"]:
        logger.warning("send_to_make called with no summary in session store.")
        return (
            "No summary found. "
            "Please generate a summary before saving."
        )

    if not store["questions"]:
        logger.warning(
            "send_to_make called with no questions in session store."
        )
        return (
            "No questions found. "
            "Please generate revision questions before saving."
        )

    # ---- Build payload -----------------------------------------------------
    payload = {
        "notes": store["notes"],
        "summary": store["summary"],
        "questions": store["questions"],
    }

    logger.info(
        "POSTing to Make.com webhook. Payload: notes=%d chars, "
        "summary=%d chars, questions=%d items.",
        len(payload["notes"]),
        len(payload["summary"]),
        len(payload["questions"]),
    )

    # ---- POST to Make.com --------------------------------------------------
    try:
        response = requests.post(
            url=MAKE_WEBHOOK_URL,
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )

        # Make.com returns 200 with body "Accepted" on success.
        if response.status_code == 200:
            logger.info(
                "Make.com webhook responded with status 200. "
                "Data saved successfully."
            )
            return (
                "☁️ Session saved to Google Sheets successfully!"
            )

        # Any non-200 status is treated as a failure.
        logger.error(
            "Make.com webhook returned unexpected status: %d. Body: %s",
            response.status_code,
            response.text[:200],
        )
        return (
            f"Make.com returned status {response.status_code}. "
            "Please check your webhook configuration."
        )

    # ---- Network exceptions ------------------------------------------------
    except Timeout:
        logger.error(
            "Request to Make.com timed out after %d seconds.", _REQUEST_TIMEOUT
        )
        return (
            f"Request timed out after {_REQUEST_TIMEOUT} seconds. "
            "Please check your internet connection and try again."
        )

    except ConnectionError as e:
        logger.error("Could not connect to Make.com webhook: %s", str(e))
        return (
            "Could not connect to Make.com. "
            "Please check your internet connection and webhook URL."
        )

    except RequestException as e:
        logger.error("HTTP request to Make.com failed: %s", str(e))
        return f"Failed to reach Make.com: {str(e)}"

    # ---- Catch-all ---------------------------------------------------------
    except Exception as e:
        logger.exception(
            "Unexpected error while sending to Make.com: %s", str(e)
        )
        return (
            "An unexpected error occurred while saving. "
            "Please try again."
        )