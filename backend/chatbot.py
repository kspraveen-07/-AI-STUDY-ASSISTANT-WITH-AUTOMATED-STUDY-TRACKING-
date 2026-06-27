# backend/chatbot.py
"""
Chat-with-notes module.

Provides chat(user_message, notes, history) which answers the student's
questions using their study notes as grounding context.

The notes are injected into the system prompt on every call so the model
stays focused on the student's material rather than general knowledge.
Conversation history is maintained by the caller (gradio_app.py) and
passed in on each turn, giving the model memory of the current session.
"""

from groq import APIConnectionError, APIStatusError, RateLimitError

from backend.groq_client import client, MODEL_NAME
from backend.logger import logger
from config import MAX_TOKENS, TEMPERATURE

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

# The notes are interpolated at call time so every request is grounded
# in the student's actual material.
_SYSTEM_PROMPT_TEMPLATE = """You are an AI Study Assistant.

Your ONLY source of information is the study notes provided below.

Rules:
1. Answer ONLY using information present in the study notes.
2. Never use outside knowledge.
3. Never guess or make up facts.
4. If the answer is not found in the notes, reply exactly:
   "I couldn't find that information in the uploaded study notes."
5. If the student asks for a simpler explanation, explain ONLY using the notes.
6. If the student asks for examples, give examples ONLY if they exist in the notes.
7. Keep answers clear, short and suitable for exam preparation.

========== STUDY NOTES ==========
{notes}
========== END OF NOTES ==========

Answer the student's questions using only the content above."""


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def chat(
    user_message: str,
    notes: str,
    history: list[dict] | None = None,
) -> str:
    """
    Generate a context-aware reply to the student's question.

    Args:
        user_message: The student's current question or message.
        notes:        The study notes stored in the session. Used to
                      ground the model's responses.
        history:      List of previous turns in OpenAI message format:
                      [{"role": "user"|"assistant", "content": str}, ...]
                      Pass None or [] to start a fresh conversation.

    Returns:
        The assistant's reply as a plain string on success.
        A user-friendly error message string on failure.

    Raises:
        Does not raise — all exceptions are caught and returned as
        descriptive strings so the UI always receives a displayable value.
    """
    # ---- Input validation --------------------------------------------------
    if not user_message or not user_message.strip():
        logger.warning("chat() called with empty user message.")
        return "Please type a question before sending."

    if not notes or not notes.strip():
        logger.warning("chat() called with no notes in session.")
        return (
            "No study notes found. "
            "Please paste your notes and generate a summary first."
        )

    logger.info(
        "Chat request received. Message length: %d chars. "
        "Notes length: %d chars. History turns: %d.",
        len(user_message),
        len(notes),
        len(history) if history else 0,
    )

    # ---- Build message list ------------------------------------------------
    # Structure: system prompt (with notes) → history → new user message.
    # This gives the model full context on every turn.
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(notes=notes)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Append previous turns so the model has conversation memory.
    if history:
        messages.extend(history)

    # Append the new user message.
    messages.append({"role": "user", "content": user_message.strip()})

    # ---- API call ----------------------------------------------------------
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        reply = response.choices[0].message.content.strip()

        logger.info(
            "Chat reply generated successfully. Reply length: %d chars.",
            len(reply),
        )
        return reply

    # ---- Specific Groq exceptions ------------------------------------------
    except RateLimitError:
        logger.error("Groq rate limit reached during chat.")
        return "Rate limit reached. Please wait a moment and try again."

    except APIConnectionError as e:
        logger.error("Groq connection error during chat: %s", str(e))
        return (
            "Could not connect to the Groq API. "
            "Please check your internet connection and try again."
        )

    except APIStatusError as e:
        logger.error(
            "Groq API status error during chat. Status: %s | Message: %s",
            e.status_code,
            str(e),
        )
        return (
            f"Groq API error (status {e.status_code}). "
            "Please check your API key and try again."
        )

    # ---- Catch-all ---------------------------------------------------------
    except Exception as e:
        logger.exception("Unexpected error during chat: %s", str(e))
        return (
            "An unexpected error occurred during the chat. "
            "Please try again."
        )