import re
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from langchain.tools import tool

from src.retrieval import retriever

# ── File-based logging setup ────────────────────────────────────────────────
_LOGS_DIR = Path("logs")
_LOGS_DIR.mkdir(exist_ok=True)

_log_file = _LOGS_DIR / f"tool_calls_{datetime.now().strftime('%Y-%m-%d')}.log"
_file_handler = logging.FileHandler(_log_file, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.addHandler(_file_handler)


class ToolLogger:
    """Logs every tool invocation to logs/<date>.log and to the Python logger."""

    @staticmethod
    def log(tool_name: str, input_data: str, output: str) -> None:
        logger.info("[Tool: %s] Input: %.200s", tool_name, input_data)
        logger.info("[Tool: %s] Output: %.200s", tool_name, output)


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
            # Strip thousands-separator commas before validation
            clean_expr = expression.replace(",", "").strip()

            # Safety check: only allow digits and basic operators
            safe_pattern = r'^[\d\s\+\-\*\/\.\(\)\%]+$'
            if not re.match(safe_pattern, clean_expr):
                return (
                    f"Error: Expression '{expression}' contains unsupported characters. "
                    "Only digits and + - * / ( ) . % are allowed."
                )

            result = eval(clean_expr, {"__builtins__": {}}, {})  # noqa: S307

            # Format result: integer-valued floats without decimal point
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
            return "Error: Division by zero."
        except Exception as exc:
            return f"Error evaluating expression: {exc}"

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
            # Return document catalogue when asked
            if query.strip().lower() in ("list", "list documents", "available documents", ""):
                doc_list = _build_doc_list()
                return f"Available documents:\n{doc_list}"

            # Try exact ID lookup first
            doc = retriever.get_document(query)
            if doc:
                output = f"[Document ID: {query}]\nTitle: {doc['title']}\n\n{doc['content']}"
                ToolLogger.log("document_reader", query, output[:80])
                return output

            # Fall back to keyword search across ALL documents (including uploads)
            results = retriever.search_documents(query, top_k=3)
            if not results:
                # Last resort: return all documents so the LLM has something to work with
                all_docs = list(retriever.documents.items())
                if all_docs:
                    parts = [f"[Document ID: {did}]\nTitle: {d['title']}\n\n{d['content']}"
                             for did, d in all_docs[:2]]
                    return "\n\n" + ("=" * 60 + "\n\n").join(parts)
                return "No documents found matching your query."

            parts = []
            for doc in results:
                parts.append(
                    f"[Document ID: {doc['id']}]\nTitle: {doc['title']}\n\n{doc['content']}"
                )

            output = "\n\n" + ("=" * 60) + "\n\n".join(parts)
            ToolLogger.log("document_reader", query, output[:80])
            return output

        except Exception as exc:
            return f"Error retrieving document: {exc}"

    return document_reader


def create_tools() -> List:
    """Create and return all agent tools."""
    return [
        create_calculator_tool(),
        create_document_reader_tool(),
    ]
