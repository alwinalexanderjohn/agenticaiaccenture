"""Entry point for the Document Assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

from src.assistant import DocumentAssistant
from src.retrieval import retriever


WELCOME = """
╔════════════════════════════════════════════════════════════╗
║             Document Assistant (LangGraph)                 ║
╠════════════════════════════════════════════════════════════╣
║  Built-in documents:                                       ║
║    • doc_financial_q1        – Q1 2026 Financial Report    ║
║    • doc_financial_q2        – Q2 2026 Financial Report    ║
║    • doc_healthcare_stats    – Healthcare Statistics 2026  ║
║    • doc_healthcare_outcomes – Patient Outcomes 2026       ║
╠════════════════════════════════════════════════════════════╣
║  Commands:                                                 ║
║    upload <filepath>  – Load a .txt / .md / .csv / .pdf    ║
║    docs               – List all available documents       ║
║    info               – Show session info                  ║
║    quit / exit        – Quit                               ║
╠════════════════════════════════════════════════════════════╣
║  Example questions:                                        ║
║    "What was the net profit in Q1 2026?"                   ║
║    "Summarize the healthcare statistics report"            ║
║    "What is the total revenue across Q1 and Q2?"           ║
╚════════════════════════════════════════════════════════════╝
"""


def _print_docs() -> None:
    """Print all currently loaded documents."""
    docs = retriever.list_documents()
    print(f"\n  {len(docs)} document(s) available:")
    for d in docs:
        print(f"    • {d['id']:35s}  [{d['type']}]  {d['title']}")


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Copy .env.example to .env and add your key.")
        return

    print(WELCOME)

    assistant = DocumentAssistant(model_name="gpt-4o")
    assistant.start_session(user_id="user_001")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # ── Built-in commands ──────────────────────────────────────────
        lower = user_input.lower()

        if lower in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        if lower == "info":
            print(f"\n[Session Info] {assistant.get_session_info()}")
            continue

        if lower == "docs":
            _print_docs()
            continue

        if lower.startswith("upload "):
            file_path = user_input[7:].strip().strip('"').strip("'")
            print(f"  Uploading: {file_path} …")
            result = retriever.load_document(file_path)
            if result.startswith("Error"):
                print(f"  {result}")
            else:
                print(f"  ✓ Document loaded with ID: '{result}'")
                print(f"  You can now ask questions like: \"Summarize {result}\"")
            continue

        # ── Send to assistant ──────────────────────────────────────────
        print("\nAssistant: ", end="", flush=True)
        try:
            response = assistant.process_message(user_input)
            print(response)
        except Exception as exc:
            print(f"[Error] {exc}")


if __name__ == "__main__":
    main()
