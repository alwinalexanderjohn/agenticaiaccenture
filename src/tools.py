import re
import logging
from typing import List

from langchain.tools import tool

from src.retrieval import retriever

logger = logging.getLogger(__name__)


class ToolLogger:
    """Simple logger for tracking tool invocations."""

    @staticmethod
    def log(tool_name: str, input_data: str, output: str) -> None:
        logger.info("[Tool: %s] Input: %.120s", tool_name, input_data)
        logger.info("[Tool: %s] Output: %.120s", tool_name, output)


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

    @tool
    def document_reader(query: str) -> str:
        """Search and retrieve financial or healthcare document content.

        Pass a document ID (e.g. "doc_financial_q1") to fetch that exact document,
        or pass keywords (e.g. "Q2 revenue profit") to find the most relevant documents.

        Available document IDs:
          - doc_financial_q1   : Q1 2024 Financial Report
          - doc_financial_q2   : Q2 2024 Financial Report
          - doc_healthcare_stats    : Healthcare Statistics 2024
          - doc_healthcare_outcomes : Patient Outcomes Report 2024

        Args:
            query: A document ID or keyword search string.

        Returns:
            The full content of the matching document(s).
        """
        try:
            # Try exact ID lookup first
            doc = retriever.get_document(query)
            if doc:
                output = f"[Document ID: {query}]\nTitle: {doc['title']}\n\n{doc['content']}"
                ToolLogger.log("document_reader", query, output[:80])
                return output

            # Fall back to keyword search
            results = retriever.search_documents(query)
            if not results:
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
