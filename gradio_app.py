# gradio_app.py
"""
Gradio UI for AI Study Assistant.

Defines the student-facing interface and wires every UI action to the
appropriate backend function via direct Python calls — no internal HTTP.

The public function build_gradio_ui() returns a gr.Blocks instance that
app.py mounts onto Flask using gr.mount_gradio_app().

Layout:
    Row 1 — Notes input (left) | Summary output (right)
    Row 2 — Questions output (full width)
    Row 3 — Action buttons: Summarise | Generate Questions | Save | Clear
    Row 4 — Status message bar
    Row 5 — Chat section: history display + message input + Send button
"""

import gradio as gr

from backend.chatbot import chat
from backend.logger import logger
from backend.question_generator import generate_questions
from backend.session_store import (
    clear_store,
    get_store,
    save_notes,
    save_results,
)
from backend.summarizer import summarize_notes
from backend.webhook import send_to_make
from backend.pdf_reader import extract_text_from_pdf


# ---------------------------------------------------------------------------
# Event handler functions
# ---------------------------------------------------------------------------
# Each function corresponds to exactly one button in the UI.
# They are plain Python functions — Gradio calls them when the matching
# button is clicked and passes the current widget values as arguments.

def handle_summarise(notes: str) -> tuple[str, str]:
    """
    Save notes to session store and generate a summary.

    Args:
        notes: Text from the notes textbox.

    Returns:
        Tuple of (summary_text, status_message) for the two output widgets.
    """
    if not notes or not notes.strip():
        return "", "Please paste your study notes first."

    store = get_store()

    if store["notes"] != notes.strip():
        save_notes(notes)

    logger.info("UI: Summarise button clicked.")

    summary = summarize_notes(notes)

    if not summary.startswith(("Please", "Rate", "Could", "Groq", "An")):
        save_results(summary=summary)
        return summary, "✅ Summary generated successfully!!."

    return "", summary


def handle_generate_questions(notes: str) -> tuple[str, str]:
    """
    Save notes to session store and generate revision questions.

    Questions are saved to the session store immediately so webhook.py
    can reuse them without a second Groq call.

    Args:
        notes: Text from the notes textbox.

    Returns:
        Tuple of (questions_text, status_message) for the two output widgets.
    """
    if not notes or not notes.strip():
        return "", "Please paste your study notes first."

    store = get_store()

    if store["notes"] != notes.strip():
        save_notes(notes)

    logger.info("UI: Generate Questions button clicked.")

    result = generate_questions(notes)

    if isinstance(result, list):
        save_results(questions=result)

        formatted = "\n".join(
            f"{i + 1}. {q}" for i, q in enumerate(result)
        )

        return formatted, f"✅ Generated {len(result)} revision questions successfully!"

    return "", result


def handle_save() -> str:
    """
    Send the current session data to Make.com and return a status message.

    Returns:
        Status message string for the status widget.
    """
    logger.info("UI: Save to Google Sheets button clicked.")
    return send_to_make()


def handle_clear() -> tuple[str, str, str, str, list]:
    """
    Clear the session store and reset all UI widgets to their empty state.

    Returns:
        Tuple matching the output widgets in order:
        (notes, summary, questions, status, chat_history)
    """
    logger.info("UI: Clear button clicked.")
    clear_store()
    return "", "", "", "🗑 Session cleared successfully. Ready for a new study session.", []


def handle_chat(
    user_message: str,
    history: list,
):
    """
    Handle chat messages for Gradio 6.
    """

    if not user_message or not user_message.strip():
        return "", history

    logger.info("UI: Chat message sent.")

    store = get_store()

    reply = chat(
        user_message=user_message.strip(),
        notes=store["notes"],
        history=history,
    )

    history = history + [
        {
            "role": "user",
            "content": user_message.strip(),
        },
        {
            "role": "assistant",
            "content": reply,
        },
    ]

    return "", history

def handle_pdf_upload(pdf_file: str) -> str:
    """
    Extract text from an uploaded PDF and return it to the Notes textbox.
    """

    if pdf_file is None:
        return ""

    try:
        return extract_text_from_pdf(pdf_file)
    except Exception as e:
        logger.exception("Failed to read PDF.")
        return f"Error reading PDF: {e}"

# ---------------------------------------------------------------------------
# UI builder
# ---------------------------------------------------------------------------

def build_gradio_ui() -> gr.Blocks:
    """
    Construct and return the complete Gradio UI as a gr.Blocks instance.

    Called once by app.py. The returned object is mounted onto Flask via
    gr.mount_gradio_app(flask_app, build_gradio_ui(), path="/").

    Returns:
        Configured gr.Blocks instance (not yet launched).
    """
    with gr.Blocks(
    title="🎓 AI Study Assistant Pro",
    css="""
    body {
        background: #0f172a;
    }

    .gradio-container {
        max-width: 1400px !important;
        margin: auto !important;
    }

    h1 {
        text-align: center;
        font-size: 42px !important;
        font-weight: 700 !important;
        margin-bottom: 10px !important;
    }

    h2, h3 {
        color: #2563eb !important;
        font-weight: 600 !important;
    }

    .gr-button {
        border-radius: 12px !important;
        font-weight: bold !important;
        transition: all 0.25s ease;
    }

    .gr-button:hover {
        transform: translateY(-2px);
    }

    textarea {
        border-radius: 12px !important;
    }

    .gr-chatbot {
        border-radius: 14px !important;
    }

    footer {
        display: none !important;
    }
    """
) as ui:

        # ---- Header --------------------------------------------------------
        gr.Markdown(
    """
# 🎓 AI Study Assistant Pro

### Learn Smarter with AI

Upload a **PDF** or paste your study notes to:

- 📚 Generate concise AI summaries
- ❓ Create revision questions
- 🤖 Chat with your study material
- ☁️ Save your session to Google Sheets

---
"""
)

        # ---- Row 1: Notes + Summary ----------------------------------------
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📄 Upload Study Material (PDF)")

                pdf_input = gr.File(
                    show_label=False,
                    file_types=[".pdf"],
                    type="filepath",
                )

                gr.Markdown("### 📝 Study Notes")

                notes_input = gr.Textbox(
                    show_label=False,
                    placeholder=(
                        "📚 Paste your study notes here or upload a PDF above...\n\n"
                        "The more detail you include, the better the "
                        "summary and questions will be."
                    ),
                    lines=15,
                    max_lines=30,
                )

            with gr.Column(scale=1):
                gr.Markdown("### 📚 AI Summary")
                summary_output = gr.Textbox(
                    show_label=False,
                    placeholder="Your summary will appear here...",
                    lines=15,
                    max_lines=30,
                    interactive=False,
                )

        # ---- Row 2: Questions ----------------------------------------------
        gr.Markdown("### ❓ Revision Questions")
        questions_output = gr.Textbox(
            show_label=False,
            placeholder="Your revision questions will appear here...",
            lines=8,
            max_lines=15,
            interactive=False,
        )

        # ---- Row 3: Action buttons -----------------------------------------
        with gr.Row():
            btn_summarise = gr.Button(
                "⚡Summarise Notes",
                variant="primary",
            )
            btn_questions = gr.Button(
                "🧠Generate Questions",
                variant="primary",
            )
            btn_save = gr.Button(
                "☁ Save Session",
                variant="secondary",
            )
            btn_clear = gr.Button(
                "🗑 Clear Session",
                variant="stop",
            )

        # ---- Row 4: Status bar ---------------------------------------------
        status_output = gr.Textbox(
            show_label=False,
            value="🚀 Ready! Upload a PDF or paste your study notes to begin.",
            interactive=False,
            elem_classes=["status-box"],
        )

        # ---- Row 5: Chat section -------------------------------------------
        gr.Markdown("---")
        gr.Markdown(
            """
            ## 🤖 AI Study Chat
            ### Chat with Your Notes
            Ask questions about your study material.
            Generate a summary first so your notes are loaded.
            """
        )

        # Gradio State holds the chat history between turns.
        # It lives server-side and is passed to/from event handlers
        # automatically — the student never sees it directly.
        chat_history_state = gr.State([])

        gr.Markdown("### 💬 Conversation")
        chatbot_display = gr.Chatbot(
            label="Chat",
            height=400,
            show_label=False,
        )

        with gr.Row():
            chat_input = gr.Textbox(
                placeholder="Ask a question about your notes...",
                show_label=False,
                scale=5,
                container=False,
            )
            btn_send = gr.Button(
                "➤ Send",
                variant="primary",
                scale=1,
            )

        # ---- Wire up events ------------------------------------------------
        
        # PDF Upload
        pdf_input.change(
            fn=handle_pdf_upload,
            inputs=[pdf_input],
            outputs=[notes_input],
        )

        # Summarise button.
        btn_summarise.click(
            fn=handle_summarise,
            inputs=[notes_input],
            outputs=[summary_output, status_output],
        )

        # Generate Questions button.
        btn_questions.click(
            fn=handle_generate_questions,
            inputs=[notes_input],
            outputs=[questions_output, status_output],
        )

        # Save button — no inputs needed (reads from session store internally).
        btn_save.click(
            fn=handle_save,
            inputs=[],
            outputs=[status_output],
        )

        # Clear button — resets all widgets and session store.
        btn_clear.click(
            fn=handle_clear,
            inputs=[],
            outputs=[
                notes_input,
                summary_output,
                questions_output,
                status_output,
                chatbot_display,
            ],
        )

        # Send button in chat.
        btn_send.click(
            fn=handle_chat,
            inputs=[chat_input, chat_history_state],
            outputs=[chat_input, chat_history_state],
        ).then(
            # After state updates, refresh the visible chatbot display.
            fn=lambda history: history,
            inputs=[chat_history_state],
            outputs=[chatbot_display],
        )

        # Also allow pressing Enter in the chat input to send.
        chat_input.submit(
            fn=handle_chat,
            inputs=[chat_input, chat_history_state],
            outputs=[chat_input, chat_history_state],
        ).then(
            fn=lambda history: history,
            inputs=[chat_history_state],
            outputs=[chatbot_display],
        )

    logger.info("Gradio UI built successfully.")
    return ui