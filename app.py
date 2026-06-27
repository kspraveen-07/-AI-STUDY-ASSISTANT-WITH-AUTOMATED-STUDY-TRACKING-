"""
app.py

Entry point for the AI Study Assistant.
Compatible with Python 3.12 + Gradio 6.x
"""

from backend.logger import logger
from gradio_app import build_gradio_ui


def main():
    logger.info("Starting AI Study Assistant...")

    demo = build_gradio_ui()

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )


if __name__ == "__main__":
    main()