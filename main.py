"""Entry point for the Document Assistant — menu-driven CLI."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from src.assistant import DocumentAssistant
from src.retrieval import retriever


# ── Colour helpers (Windows-safe) ─────────────────────────────────────────────
def _c(code: str, text: str) -> str:
    """Wrap text in an ANSI colour code if the terminal supports it."""
    if sys.stdout.isatty() and os.name != "nt" or os.environ.get("TERM"):
        return f"\033[{code}m{text}\033[0m"
    return text

G  = lambda t: _c("32", t)   # green
B  = lambda t: _c("34", t)   # blue
Y  = lambda t: _c("33", t)   # yellow
C  = lambda t: _c("36", t)   # cyan
R  = lambda t: _c("31", t)   # red
BD = lambda t: _c("1",  t)   # bold


WELCOME = """
╔══════════════════════════════════════════════════════════════╗
║           🏥  Document Assistant  (LangGraph + GPT-4o)       ║
╠══════════════════════════════════════════════════════════════╣
║  Built-in documents:                                         ║
║    doc_financial_q1        –  Q1 2026 Financial Report       ║
║    doc_financial_q2        –  Q2 2026 Financial Report       ║
║    doc_healthcare_stats    –  Healthcare Statistics 2026     ║
║    doc_healthcare_outcomes –  Patient Outcomes Report 2026   ║
╚══════════════════════════════════════════════════════════════╝
"""

MENU = """
  ┌─────────────────────────────────────────┐
  │           Choose an option              │
  ├─────────────────────────────────────────┤
  │  1  📁  Upload Document                 │
  │  2  ❓  Question & Answer               │
  │  3  📄  Summarize Document              │
  │  4  🧮  Calculator                      │
  │  5  📚  Show Loaded Documents           │
  │  6  ℹ️   Session Info                   │
  │  0  ❌  Quit                            │
  └─────────────────────────────────────────┘
"""


# ── File-picker via tkinter (opens native OS dialog) ──────────────────────────
def _pick_file() -> str | None:
    """Open a native file-browser dialog and return the chosen path (or None)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()          # hide the blank Tk window
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Select a document to upload",
            filetypes=[
                ("Supported files", "*.pdf *.txt *.md *.csv"),
                ("PDF",  "*.pdf"),
                ("Text", "*.txt"),
                ("Markdown", "*.md"),
                ("CSV",  "*.csv"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return path if path else None
    except Exception as exc:
        print(R(f"  File dialog unavailable ({exc})."))
        return None


def _upload_flow() -> None:
    print(Y("\n  Opening file browser … (a dialog window will appear)"))
    file_path = _pick_file()

    if not file_path:
        # Fallback: let user type the path manually
        print(Y("  No file selected. Enter path manually (or press Enter to cancel):"))
        try:
            file_path = input("  Path: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            file_path = ""

    if not file_path:
        print("  Cancelled.")
        return

    print(f"  Uploading: {file_path} …")
    result = retriever.load_document(file_path)
    if result.startswith("Error"):
        print(R(f"  {result}"))
    else:
        print(G(f"  ✓ Loaded — document ID: '{result}'"))
        print(f"  Try: option 3 → \"Summarize {result}\"")


def _qa_flow(assistant: DocumentAssistant) -> None:
    print(B("\n  Enter your question (or press Enter to cancel):"))
    try:
        question = input("  ❓ ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not question:
        print("  Cancelled.")
        return
    print(BD("\n  Assistant:"), flush=True)
    try:
        print(assistant.process_message(question))
    except Exception as exc:
        print(R(f"  [Error] {exc}"))


def _summarize_flow(assistant: DocumentAssistant) -> None:
    print(C("\n  What would you like summarized?"))
    print("  (Enter a document ID, topic, or 'all' for all loaded docs.)")
    print("  Examples:  doc_financial_q1  |  healthcare report  |  all")
    try:
        topic = input("  📄 ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not topic:
        print("  Cancelled.")
        return
    prompt = f"Please summarize: {topic}"
    print(BD("\n  Assistant:"), flush=True)
    try:
        print(assistant.process_message(prompt))
    except Exception as exc:
        print(R(f"  [Error] {exc}"))


def _calculator_flow(assistant: DocumentAssistant) -> None:
    print(Y("\n  What would you like to calculate?"))
    print("  Examples:  total revenue Q1 and Q2  |  average cost per patient  |  net profit margin")
    try:
        question = input("  🧮 ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not question:
        print("  Cancelled.")
        return
    prompt = f"Calculate: {question}"
    print(BD("\n  Assistant:"), flush=True)
    try:
        print(assistant.process_message(prompt))
    except Exception as exc:
        print(R(f"  [Error] {exc}"))


def _print_docs() -> None:
    docs = retriever.list_documents()
    print(f"\n  {len(docs)} document(s) loaded:")
    for d in docs:
        print(f"    • {BD(d['id']):<40}  [{d['type']}]  {d['title']}")


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(R("ERROR: OPENAI_API_KEY not found. Add it to your .env file."))
        return

    print(WELCOME)

    assistant = DocumentAssistant(model_name="gpt-4o")
    assistant.start_session(user_id="user_001")

    while True:
        print(MENU)
        try:
            choice = input("  Enter option (0-6): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if choice == "0":
            print("  Goodbye!")
            break
        elif choice == "1":
            _upload_flow()
        elif choice == "2":
            _qa_flow(assistant)
        elif choice == "3":
            _summarize_flow(assistant)
        elif choice == "4":
            _calculator_flow(assistant)
        elif choice == "5":
            _print_docs()
        elif choice == "6":
            print(f"\n  Session Info: {assistant.get_session_info()}")
        else:
            print(R("  Invalid option. Please enter a number from 0 to 6."))

        input("\n  Press Enter to return to the menu …")


if __name__ == "__main__":
    main()
