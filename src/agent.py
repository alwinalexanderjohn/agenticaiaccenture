import operator
from typing import Annotated, Any, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from src.prompts import (
    QA_SYSTEM_PROMPT,
    SUMMARIZATION_SYSTEM_PROMPT,
    CALCULATION_SYSTEM_PROMPT,
    get_chat_prompt_template,
    get_intent_classification_prompt,
)
from src.retrieval import retriever
from src.schemas import (
    AnswerResponse,
    CalculationResponse,
    SummarizationResponse,
    UserIntent,
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """Full state schema for the document assistant LangGraph workflow."""
    user_input: str
    messages: Annotated[List[BaseMessage], add_messages]
    intent: Optional[UserIntent]
    next_step: str
    conversation_summary: str
    active_documents: List[str]
    current_response: Optional[Any]
    tools_used: List[str]
    session_id: str
    user_id: str
    # operator.add accumulates node names across all nodes that run in a turn
    actions_taken: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _available_docs_hint() -> str:
    """Return a formatted string listing all documents currently in the store."""
    docs = retriever.list_documents()
    lines = [f"  - {d['id']} : {d['title']}" for d in docs]
    return "Available documents in the store:\n" + "\n".join(lines)


def _direct_retrieve(user_input: str) -> list[str]:
    """Fallback: directly search the retriever when the tool loop retrieved nothing."""
    results = retriever.search_documents(user_input, top_k=3)
    if not results:
        results = [
            {"id": did, "title": d["title"], "content": d["content"]}
            for did, d in list(retriever.documents.items())[:2]
        ]
    return [
        f"[Document ID: {r['id']}]\nTitle: {r['title']}\n\n{r['content']}"
        for r in results
    ]


def _run_tool_loop(llm_with_tools, tool_map: dict, messages: list, max_iter: int = 5):
    """Execute the tool-calling loop and return (updated_messages, tools_used, context_snippets)."""
    tools_used: List[str] = []
    context_snippets: List[str] = []

    for _ in range(max_iter):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not (hasattr(response, "tool_calls") and response.tool_calls):
            break

        for tc in response.tool_calls:
            name = tc["name"]
            tools_used.append(name)
            if name in tool_map:
                result = tool_map[name].invoke(tc["args"])
                result_str = str(result)
                context_snippets.append(result_str)
                messages.append(ToolMessage(content=result_str, tool_call_id=tc["id"]))

    return messages, tools_used, context_snippets


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def classify_intent(state: AgentState, config: RunnableConfig) -> dict:
    """Node 1: Classify user intent and set the routing destination."""
    # Task 2.2 — Step 1: configure LLM with structured output
    llm = config["configurable"]["llm"]
    structured_llm = llm.with_structured_output(UserIntent)

    # Build conversation history string from recent messages
    conversation_history = "No previous conversation."
    recent = state.get("messages", [])[-6:]
    if recent:
        lines = []
        for msg in recent:
            if isinstance(msg, HumanMessage):
                lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage) and msg.content:
                lines.append(f"Assistant: {msg.content}")
        if lines:
            conversation_history = "\n".join(lines)

    # Task 2.2 — Step 2 & 3: get and format the classification prompt
    prompt = get_intent_classification_prompt()
    formatted_prompt = prompt.format(
        user_input=state["user_input"],
        conversation_history=conversation_history,
    )

    # Task 2.2 — Step 4: invoke the LLM
    intent: UserIntent = structured_llm.invoke(formatted_prompt)

    # Task 2.2 — Step 5: map intent to next node
    routing = {
        "qa": "qa_agent",
        "summarization": "summarization_agent",
        "calculation": "calculation_agent",
    }
    next_step = routing.get(intent.intent_type, "qa_agent")

    # Task 2.2 — Step 6: return updated state fields
    return {
        "intent": intent,
        "next_step": next_step,
        "actions_taken": ["classify_intent"],
    }


def qa_agent(state: AgentState, config: RunnableConfig) -> dict:
    """Node 2: Answer factual questions using retrieved document content."""
    llm = config["configurable"]["llm"]
    tools = config["configurable"]["tools"]

    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    prompt_template = get_chat_prompt_template("qa")

    # Phase 1 — gather information via tool-calling loop
    # Inject available document IDs so the LLM knows what to retrieve
    enriched_input = f"{state['user_input']}\n\n[{_available_docs_hint()}]"
    messages = prompt_template.format_messages(user_input=enriched_input)
    messages, tools_used, context_snippets = _run_tool_loop(llm_with_tools, tool_map, messages)

    # Fallback: if the LLM skipped tool calls, retrieve directly
    if not context_snippets:
        context_snippets = _direct_retrieve(state["user_input"])

    # Phase 2 — produce a structured AnswerResponse
    context_str = "\n\n".join(context_snippets)
    final_prompt = (
        f"Using the document content below, answer the question with a structured response.\n\n"
        f"Question: {state['user_input']}\n\n"
        f"Document Content:\n{context_str}\n\n"
        f"Respond with the question, a clear answer, the list of document IDs used as sources, "
        f"and a confidence score between 0.0 and 1.0."
    )
    final_response: AnswerResponse = llm.with_structured_output(AnswerResponse).invoke(final_prompt)

    return {
        "current_response": final_response,
        "messages": [
            HumanMessage(content=state["user_input"]),
            AIMessage(content=final_response.answer),
        ],
        "tools_used": tools_used,
        "actions_taken": ["qa_agent"],
    }


def summarization_agent(state: AgentState, config: RunnableConfig) -> dict:
    """Node 3: Summarize documents and extract key points."""
    llm = config["configurable"]["llm"]
    tools = config["configurable"]["tools"]

    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    prompt_template = get_chat_prompt_template("summarization")

    # Phase 1 — retrieve document content
    enriched_input = f"{state['user_input']}\n\n[{_available_docs_hint()}]"
    messages = prompt_template.format_messages(user_input=enriched_input)
    messages, tools_used, context_snippets = _run_tool_loop(llm_with_tools, tool_map, messages)

    # Fallback: if the LLM skipped tool calls, retrieve directly
    if not context_snippets:
        context_snippets = _direct_retrieve(state["user_input"])

    # Phase 2 — produce a structured SummarizationResponse
    context_str = "\n\n".join(context_snippets)
    final_prompt = (
        f"Using the document content below, create a structured summary.\n\n"
        f"Request: {state['user_input']}\n\n"
        f"Document Content:\n{context_str}\n\n"
        f"Respond with a concise summary paragraph, a list of 3 to 7 key points, "
        f"and the list of document IDs used as sources."
    )
    final_response: SummarizationResponse = llm.with_structured_output(SummarizationResponse).invoke(final_prompt)

    return {
        "current_response": final_response,
        "messages": [
            HumanMessage(content=state["user_input"]),
            AIMessage(content=final_response.summary),
        ],
        "tools_used": tools_used,
        "actions_taken": ["summarization_agent"],
    }


def calculation_agent(state: AgentState, config: RunnableConfig) -> dict:
    """Node 4: Perform calculations on data retrieved from documents."""
    llm = config["configurable"]["llm"]
    tools = config["configurable"]["tools"]

    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    prompt_template = get_chat_prompt_template("calculation")

    # Run a longer tool-calling loop so the model can call document_reader then calculator
    enriched_input = f"{state['user_input']}\n\n[{_available_docs_hint()}]"
    messages = prompt_template.format_messages(user_input=enriched_input)
    messages, tools_used, context_snippets = _run_tool_loop(llm_with_tools, tool_map, messages, max_iter=8)

    # Fallback: if the LLM skipped tool calls, retrieve directly
    if not context_snippets:
        context_snippets = _direct_retrieve(state["user_input"])

    # Phase 2 — produce a structured CalculationResponse
    context_str = "\n\n".join(context_snippets)
    final_prompt = (
        f"Based on the document data and calculator output below, provide a structured response.\n\n"
        f"Request: {state['user_input']}\n\n"
        f"Retrieved Data and Calculation Output:\n{context_str}\n\n"
        f"Respond with the original question, the final numeric result with units and context, "
        f"the mathematical expression used, and the document IDs that contained the source data."
    )
    final_response: CalculationResponse = llm.with_structured_output(CalculationResponse).invoke(final_prompt)

    return {
        "current_response": final_response,
        "messages": [
            HumanMessage(content=state["user_input"]),
            AIMessage(content=final_response.result),
        ],
        "tools_used": tools_used,
        "actions_taken": ["calculation_agent"],
    }


def update_memory(state: AgentState, config: RunnableConfig) -> dict:
    """Node 5: Summarise the conversation and track active documents."""
    # Task 2.4 — extract llm from config
    llm = config["configurable"]["llm"]

    # Build a short conversation snippet from recent messages
    recent_msgs = state.get("messages", [])[-10:]
    conv_lines = []
    for msg in recent_msgs:
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            conv_lines.append(f"{role}: {msg.content[:300]}")

    if conv_lines:
        summary_prompt = (
            "Summarise the following conversation in 1-2 sentences, focusing on which documents "
            "were discussed and what information was found:\n\n"
            + "\n".join(conv_lines)
            + "\n\nSummary:"
        )
        summary_msg = llm.invoke(summary_prompt)
        conversation_summary = summary_msg.content if hasattr(summary_msg, "content") else str(summary_msg)
    else:
        conversation_summary = state.get("conversation_summary", "")

    # Track document IDs that appeared in the current response's sources
    active_documents = list(state.get("active_documents", []))
    current_response = state.get("current_response")
    if current_response and hasattr(current_response, "sources"):
        for src in current_response.sources:
            if src and src not in active_documents:
                active_documents.append(src)

    return {
        "conversation_summary": conversation_summary,
        "active_documents": active_documents,
        "next_step": END,
        "actions_taken": ["update_memory"],
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_to_agent(state: AgentState) -> str:
    """Conditional edge: route from classify_intent to the correct agent node."""
    return state.get("next_step", "qa_agent")


# ---------------------------------------------------------------------------
# Workflow factory
# ---------------------------------------------------------------------------

def create_workflow():
    """Build, compile, and return the LangGraph workflow with an InMemorySaver checkpointer."""
    workflow = StateGraph(AgentState)

    # Task 2.5 — add all nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("qa_agent", qa_agent)
    workflow.add_node("summarization_agent", summarization_agent)
    workflow.add_node("calculation_agent", calculation_agent)
    workflow.add_node("update_memory", update_memory)

    # Entry point
    workflow.set_entry_point("classify_intent")

    # Task 2.5 — conditional edges from classify_intent to each agent
    workflow.add_conditional_edges(
        "classify_intent",
        _route_to_agent,
        {
            "qa_agent": "qa_agent",
            "summarization_agent": "summarization_agent",
            "calculation_agent": "calculation_agent",
        },
    )

    # Task 2.5 — each agent feeds into update_memory, which ends the graph
    workflow.add_edge("qa_agent", "update_memory")
    workflow.add_edge("summarization_agent", "update_memory")
    workflow.add_edge("calculation_agent", "update_memory")
    workflow.add_edge("update_memory", END)

    # Task 2.6 — compile with InMemorySaver for state persistence across invocations
    return workflow.compile(checkpointer=InMemorySaver())
