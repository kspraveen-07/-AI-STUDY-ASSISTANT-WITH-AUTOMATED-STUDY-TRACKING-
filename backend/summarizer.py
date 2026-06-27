# backend/summarizer.py
"""
Study notes summarisation module.

Provides summarize_notes(notes) which sends the student's raw study
notes to the Groq API and returns a concise, well-structured summary.

The caller (app.py) is responsible for saving the returned summary to
the session store — this module only handles the Groq interaction.
"""

from groq import APIConnectionError, APIStatusError, RateLimitError

from backend.groq_client import client, MODEL_NAME
from backend.logger import logger
from config import MAX_TOKENS, TEMPERATURE

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

# Keeping the system prompt as a module-level constant makes it easy to
# iterate on without touching any logic.
_SYSTEM_PROMPT = """You are an expert study assistant that helps students \
learn more effectively.

When given study notes, you produce a clear, concise summary that:
- Captures every key concept, definition, and fact from the notes
- Uses plain language a student can quickly review before an exam
- Is structured with short paragraphs (no bullet points unless the notes \
use them)
- Is meaningfully shorter than the original — aim for 25–35% of the \
original length
- Does not add information that is not in the notes

Respond with the summary only. Do not include preamble such as \
"Here is a summary:"."""


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def summarize_notes(notes: str) -> str:
    """
    Generate a concise summary of the provided study notes.

    Args:
        notes: Raw study notes text pasted by the student. Must be
               a non-empty string.

    Returns:
        A summary string on success.
        A user-friendly error message string on failure (so the Gradio
        UI can display it directly without crashing).

    Raises:
        Does not raise — all exceptions are caught and returned as
        descriptive strings so the UI always receives a displayable value.
    """
    # ---- Input validation --------------------------------------------------
    if not notes or not notes.strip():
        logger.warning("summarize_notes called with empty input.")
        return "Please paste your study notes before generating a summary."

    logger.info(
        "Sending summarisation request to Groq API. Input length: %d chars.",
        len(notes),
    )

    # ---- API call ----------------------------------------------------------
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": notes},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        summary = response.choices[0].message.content.strip()

        logger.info(
            "Summary generated successfully. Output length: %d chars.",
            len(summary),
        )
        return summary

    # ---- Specific Groq exceptions ------------------------------------------
    except RateLimitError:
        logger.error("Groq rate limit reached during summarisation.")
        return (
            "Rate limit reached. Please wait a moment and try again."
        )

    except APIConnectionError as e:
        logger.error("Groq connection error during summarisation: %s", str(e))
        return (
            "Could not connect to the Groq API. "
            "Please check your internet connection and try again."
        )

    except APIStatusError as e:
        logger.error(
            "Groq API status error during summarisation. "
            "Status: %s | Message: %s",
            e.status_code,
            str(e),
        )
        return (
            f"Groq API error (status {e.status_code}). "
            "Please check your API key and try again."
        )

    # ---- Catch-all ---------------------------------------------------------
    except Exception as e:
        logger.exception(
            "Unexpected error during summarisation: %s", str(e)
        )
        return (
            "An unexpected error occurred while generating the summary. "
            "Please try again."
        )