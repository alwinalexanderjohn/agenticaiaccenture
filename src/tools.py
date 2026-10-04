import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from langchain.tools import tool

from src.retrieval import retriever

# ── Logs directory ──────────────────────────────────────────────────────────
_LOGS_DIR = Path("logs")
_LOGS_DIR.mkdir(exist_ok=True)

# Module-level session context — set by DocumentAssistant.start_session()
_current_session_id: str = "unknown"


def set_session_context(session_id: str) -> None:
    """Called by DocumentAssistant so tool logs are written to the session's own file."""
    global _current_session_id
    _current_session_id = session_id


class ToolLogger:
    """Appends every tool invocation to logs/<session_id>.log."""

    @staticmethod
    def log(tool_name: str, input_data: str, output: str, status: str = "OK") -> None:
        log_file = _LOGS_DIR / f"{_current_session_id}.log"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]  Tool: {tool_name}  |  Status: {status}\n")
            f.write(f"  Input:  {input_data}\n")
            f.write(f"  Output: {output}\n\n")

        # Also emit to Python logger for console visibility
        logging.getLogger(__name__).info(
            "[%s] %s → %s", tool_name, input_data[:120], output[:120]
        )


def create_calculator_tool():
    """Return a LangChain tool that safely evaluates mathematical expressions."""

    @tool
    def calculator(expression: str) -> str:
        """Evaluate a mathematical expression and return the numeric result.

        Use this tool for ALL calculations — no matter how simple.
        Only basic arithmetic operators are supported: + - * / ( ) . %

        Args:
            expression: A math expression string, e.g. "4200000 - 2800000" or "5100000 / 13421"

        Returns:
            A formatted string showing the result.
        """
        try:
            clean_expr = expression.replace(",", "").strip()
            safe_pattern = r'^[\d\s\+\-\*\/\.\(\)\%]+$'
            if not re.match(safe_pattern, clean_expr):
                msg = (
                    f"Error: Expression '{expression}' contains unsupported characters. "
                    "Only digits and + - * / ( ) . % are allowed."
                )
                ToolLogger.log("calculator", expression, msg, status="INVALID_INPUT")
                return msg

            result = eval(clean_expr, {"__builtins__": {}}, {})  # noqa: S307

            if isinstance(result, float) and result == int(result):
                formatted = f"{int(result):,}"
            elif isinstance(result, float):
                formatted = f"{result:,.6f}".rstrip("0").rstrip(".")
            else:
                formatted = f"{result:,}"

            output = f"Result: {formatted}  (expression: {expression})"
            ToolLogger.log("calculator", expression, output)
            return output

        except ZeroDivisionError:
            msg = "Error: Division by zero."
            ToolLogger.log("calculator", expression, msg, status="ZERO_DIVISION")
            return msg
        except Exception as exc:
            msg = f"Error evaluating expression: {exc}"
            ToolLogger.log("calculator", expression, msg, status="ERROR")
            return msg

    return calculator


def create_document_reader_tool():
    """Return a LangChain tool that retrieves document content."""

    def _build_doc_list() -> str:
        docs = retriever.list_documents()
        return "\n".join(f"  - {d['id']} : {d['title']}" for d in docs)

    @tool
    def document_reader(query: str) -> str:
        """Search and retrieve document content from the available document store.

        Pass a document ID to fetch that exact document, or pass any keywords
        to find the most relevant documents. ALWAYS call this tool first before
        answering — never reply without retrieving document content.

        To see which documents are available, pass query="list" and all document
        IDs and titles will be returned.

        Args:
            query: A document ID, the word "list", or any keyword search string.

        Returns:
            The full content of the matching document(s), or a list of available IDs.
        """
        try:
            # ── Path 1: catalogue listing ────────────────────────────────────
            if query.strip().lower() in ("list", "list documents", "available documents", ""):
                doc_list = _build_doc_list()
                output = f"Available documents:\n{doc_list}"
                ToolLogger.log("document_reader", query, output, status="LIST")
                return output

            # ── Path 2: exact document ID lookup ─────────────────────────────
            doc = retriever.get_document(query)
            if doc:
                output = f"[Document ID: {query}]\nTitle: {doc['title']}\n\n{doc['content']}"
                ToolLogger.log("document_reader", query, output, status="EXACT_MATCH")
                return output

            # ── Path 3: keyword search ───────────────────────────────────────
            results = retriever.search_documents(query, top_k=3)
            if results:
                parts = [
                    f"[Document ID: {r['id']}]\nTitle: {r['title']}\n\n{r['content']}"
                    for r in results
                ]
                output = ("\n\n" + "=" * 60 + "\n\n").join(parts)
                ToolLogger.log("document_reader", query, output, status="KEYWORD_MATCH")
                return output

            # ── Path 4: last-resort — return all documents ───────────────────
            all_docs = list(retriever.documents.items())
            if all_docs:
                parts = [
                    f"[Document ID: {did}]\nTitle: {d['title']}\n\n{d['content']}"
                    for did, d in all_docs[:2]
                ]
                output = ("\n\n" + "=" * 60 + "\n\n").join(parts)
                ToolLogger.log("document_reader", query, output, status="FALLBACK_ALL")
                return output

            msg = "No documents found matching your query."
            ToolLogger.log("document_reader", query, msg, status="NO_MATCH")
            return msg

        except Exception as exc:
            msg = f"Error retrieving document: {exc}"
            ToolLogger.log("document_reader", query, msg, status="ERROR")
            return msg

    return document_reader


def create_tools() -> List:
    """Create and return all agent tools."""
    return [
        create_calculator_tool(),
        create_document_reader_tool(),
    ]
