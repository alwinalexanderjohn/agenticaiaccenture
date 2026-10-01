import uuid
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI

from src.agent import AgentState, create_workflow
from src.tools import create_tools


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@dataclass
class Session:
    """Represents a single conversation session."""
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    is_first_message: bool = True
    message_count: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "message_count": self.message_count,
        }


# ---------------------------------------------------------------------------
# DocumentAssistant
# ---------------------------------------------------------------------------

class DocumentAssistant:
    """Main assistant class that manages the LangGraph workflow and conversation sessions."""

    def __init__(self, model_name: str = "gpt-4o", sessions_dir: str = "sessions"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.tools = create_tools()
        self.workflow = create_workflow()
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.current_session: Optional[Session] = None

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_session(self, user_id: str = "default_user") -> str:
        """Start a new conversation session and return its ID."""
        session_id = str(uuid.uuid4())
        self.current_session = Session(session_id=session_id, user_id=user_id)
        print(f"[Session started] ID: {session_id}")
        return session_id

    def save_session(self) -> None:
        """Persist the current session metadata to disk."""
        if not self.current_session:
            return
        path = self.sessions_dir / f"{self.current_session.session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.current_session.to_dict(), f, indent=2)

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------

    def process_message(self, user_input: str) -> str:
        """Process a user message and return the assistant's response.

        Args:
            user_input: The user's raw text input.

        Returns:
            A plain-text response string.
        """
        if not self.current_session:
            self.start_session()

        # Task 2.6 — set thread_id, llm, and tools in the configurable dict
        config = {
            "configurable": {
                "thread_id": self.current_session.session_id,
                "llm": self.llm,
                "tools": self.tools,
            }
        }

        # On the first message of a session, supply the full initial state.
        # On subsequent messages LangGraph loads the checkpoint and we only
        # need to supply the fields that change.
        if self.current_session.is_first_message:
            state: dict = {
                "user_input": user_input,
                "messages": [],
                "intent": None,
                "next_step": "",
                "conversation_summary": "",
                "active_documents": [],
                "current_response": None,
                "tools_used": [],
                "session_id": self.current_session.session_id,
                "user_id": self.current_session.user_id,
                "actions_taken": [],
            }
            self.current_session.is_first_message = False
        else:
            state = {"user_input": user_input, "tools_used": [], "current_response": None}

        # Invoke the compiled graph
        result = self.workflow.invoke(state, config=config)

        self.current_session.message_count += 1
        self.save_session()

        return self._extract_response(result, user_input)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_response(self, result: dict, fallback_input: str) -> str:
        """Extract a human-readable string from the graph result."""
        current_response = result.get("current_response")

        if current_response is not None:
            if hasattr(current_response, "answer"):
                return current_response.answer
            if hasattr(current_response, "summary"):
                key_points = getattr(current_response, "key_points", [])
                text = current_response.summary
                if key_points:
                    text += "\n\nKey Points:\n" + "\n".join(f"  • {p}" for p in key_points)
                return text
            if hasattr(current_response, "result"):
                return current_response.result

        # Fall back to last AI message in history
        for msg in reversed(result.get("messages", [])):
            from langchain_core.messages import AIMessage
            if isinstance(msg, AIMessage) and msg.content:
                return str(msg.content)

        return "I was unable to generate a response. Please try again."

    def get_session_info(self) -> dict:
        """Return metadata about the current session."""
        if not self.current_session:
            return {"status": "no active session"}
        return self.current_session.to_dict()
