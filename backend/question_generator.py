# backend/question_generator.py
"""
Revision question generation module.

Provides generate_questions(notes) which sends the student's study notes
to the Groq API and returns a list of 5-10 revision questions.

The returned list is saved to the session store by the caller (app.py)
and is later reused by webhook.py when sending data to Make.com.
Questions are generated exactly once — never re-generated for the webhook.
"""

import re

from groq import APIConnectionError, APIStatusError, RateLimitError

from backend.groq_client import client, MODEL_NAME
from backend.logger import logger
from config import MAX_TOKENS, TEMPERATURE

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum and maximum number of questions to request from the model.
_MIN_QUESTIONS = 5
_MAX_QUESTIONS = 10

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = f"""You are an expert study assistant that creates \
high-quality revision questions.

When given study notes, generate between {_MIN_QUESTIONS} and \
{_MAX_QUESTIONS} revision questions that:
- Test genuine understanding, not just memorisation
- Cover the most important concepts in the notes
- Vary in style (e.g. "What is...?", "Explain why...", "How does...?", \
"What is the difference between...?")
- Are self-contained — a student can answer them without re-reading \
the notes

Format rules (strictly follow these):
- Output one question per line
- Number each question: 1. 2. 3. etc.
- Do not add any preamble, headings, or closing remarks
- Do not add blank lines between questions"""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_questions(raw: str) -> list[str]:
    """
    Parse the model's raw text output into a clean list of question strings.

    Handles common model formatting variations:
        "1. What is photosynthesis?"   → "What is photosynthesis?"
        "1) What is photosynthesis?"   → "What is photosynthesis?"
        "- What is photosynthesis?"    → "What is photosynthesis?"
        "• What is photosynthesis?"    → "What is photosynthesis?"

    Args:
        raw: Raw string returned by the Groq API.

    Returns:
        List of cleaned question strings. Empty strings and whitespace-only
        lines are removed.
    """
    questions = []

    for line in raw.splitlines():
        # Strip leading/trailing whitespace from the line.
        line = line.strip()

        # Skip blank lines.
        if not line:
            continue

        # Remove common list prefixes: "1.", "1)", "-", "•", "*"
        cleaned = re.sub(r"^(\d+[\.\)]|[-•*])\s*", "", line).strip()

        if cleaned:
            questions.append(cleaned)

    logger.debug("Parsed %d questions from model output.", len(questions))
    return questions


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def generate_questions(notes: str) -> list[str] | str:
    """
    Generate revision questions from the provided study notes.

    Args:
        notes: Raw study notes text pasted by the student. Must be
               a non-empty string.

    Returns:
        A list of question strings (5-10 items) on success.
        A user-friendly error message string on failure, so the Gradio
        UI can display it directly without crashing.

    Raises:
        Does not raise — all exceptions are caught and returned as
        descriptive strings so the UI always receives a displayable value.
    """
    # ---- Input validation --------------------------------------------------
    if not notes or not notes.strip():
        logger.warning("generate_questions called with empty input.")
        return "Please paste your study notes before generating questions."

    logger.info(
        "Sending question generation request to Groq API. "
        "Input length: %d chars.",
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

        raw_output = response.choices[0].message.content.strip()
        questions = _parse_questions(raw_output)

        # Defensive check: if parsing produced nothing, return the raw output
        # as a single item so the UI always shows something meaningful.
        if not questions:
            logger.warning(
                "Question parser returned empty list. Raw output: %s",
                raw_output[:200],
            )
            return "Could not parse questions from the model response. Please try again."

        logger.info(
            "Questions generated successfully. Count: %d.", len(questions)
        )
        return questions

    # ---- Specific Groq exceptions ------------------------------------------
    except RateLimitError:
        logger.error("Groq rate limit reached during question generation.")
        return "Rate limit reached. Please wait a moment and try again."

    except APIConnectionError as e:
        logger.error(
            "Groq connection error during question generation: %s", str(e)
        )
        return (
            "Could not connect to the Groq API. "
            "Please check your internet connection and try again."
        )

    except APIStatusError as e:
        logger.error(
            "Groq API status error during question generation. "
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
            "Unexpected error during question generation: %s", str(e)
        )
        return (
            "An unexpected error occurred while generating questions. "
            "Please try again."
        )