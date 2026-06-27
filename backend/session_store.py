# backend/session_store.py
"""
In-memory session store for AI Study Assistant.

Holds the student's notes, generated summary, and generated questions
for the lifetime of the Flask server process. All reads and writes go
through the four public functions below — no other module should access
_store directly.

Limitation (by design): data is lost if the server restarts. This is
acceptable for a single-user capstone project. To add persistence later,
replace the dict with a database call inside each function — the function
signatures stay the same, so no other file needs to change.
"""

from backend.logger import logger

# ---------------------------------------------------------------------------
# Internal store — private to this module
# ---------------------------------------------------------------------------

_store: dict = {
    "notes": "",        # Raw text pasted by the student
    "summary": "",      # Generated summary from Groq
    "questions": [],    # Generated revision questions from Groq (list of str)
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def save_notes(notes: str) -> None:
    """
    Persist the student's study notes and clear any previous results.

    Clearing summary and questions on each new note submission prevents
    stale data from a previous session being sent to Make.com alongside
    new notes.

    Args:
        notes: Raw study notes text pasted by the student.
    """
    _store["notes"] = notes.strip()
    _store["summary"] = ""
    _store["questions"] = []
    logger.info("Session store updated: notes saved (%d chars).", len(_store["notes"]))


def save_results(summary: str = "", questions: list[str] | None = None) -> None:
    """
    Persist generated summary and/or questions to the store.

    Either argument may be omitted — calling save_results(summary="...")
    only updates the summary without touching the questions, and vice versa.

    Args:
        summary:   Generated summary string. Defaults to "" (no update).
        questions: List of generated revision question strings.
                   Defaults to None (no update).
    """
    if summary:
        _store["summary"] = summary
        logger.info("Session store updated: summary saved (%d chars).", len(summary))

    if questions is not None:
        _store["questions"] = questions
        logger.info(
            "Session store updated: %d questions saved.", len(questions)
        )


def get_store() -> dict:
    """
    Return a snapshot copy of the current session store.

    Returns a copy (not the live dict) so callers cannot accidentally
    mutate the store by modifying the returned value.

    Returns:
        dict with keys: "notes" (str), "summary" (str), "questions" (list[str])
    """
    snapshot = _store.copy()
    logger.debug(
        "Session store read: notes=%d chars, summary=%d chars, questions=%d items.",
        len(snapshot["notes"]),
        len(snapshot["summary"]),
        len(snapshot["questions"]),
    )
    return snapshot


def clear_store() -> None:
    """
    Reset the session store to its initial empty state.

    Useful when the student wants to start a fresh study session without
    restarting the server.
    """
    _store["notes"] = ""
    _store["summary"] = ""
    _store["questions"] = []
    logger.info("Session store cleared.")