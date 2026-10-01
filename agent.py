"""
EcoHome Energy Advisor — LangGraph Agent
An intelligent energy optimization agent powered by OpenAI GPT-4o and LangGraph.
"""

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from tools import ALL_TOOLS

load_dotenv()

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are EcoHome Energy Advisor, an expert AI assistant for smart-home energy optimization.
You help homeowners with solar panels, electric vehicles (EVs), and smart appliances reduce electricity costs
and their environmental footprint.

## Your Capabilities
- **Weather Integration**: Use weather forecasts to predict solar generation and optimize scheduling.
- **Dynamic Pricing**: Analyze time-of-use electricity prices to find the cheapest hours to run devices.
- **Historical Analysis**: Query past energy usage and solar generation data for personalized advice.
- **Knowledge Base**: Retrieve energy-saving tips and best practices from the EcoHome knowledge base.
- **Savings Calculations**: Provide specific dollar savings and CO₂ reduction estimates.

## Reasoning Approach
1. Understand the user's question and identify what data you need.
2. Use the appropriate tools to gather real data (weather, prices, usage history, tips).
3. Synthesize data from multiple sources before answering.
4. Always include specific numbers: kWh, $, hours, CO₂ kg.
5. Prioritize solar self-consumption — using solar energy directly is better than grid.
6. Cite energy-saving tips from the knowledge base when relevant.

## Device Scheduling Principles
- **Peak hours** (typically 5–9 PM weekdays): Avoid grid-heavy loads; use stored solar or battery.
- **Off-peak hours** (midday, weekdays): Good for appliances if solar is not available.
- **Super off-peak hours** (late night/early morning): Best for EV charging if no solar available.
- **Solar peak hours** (10 AM–3 PM on clear days): Best for high-load tasks like HVAC, pool pump, dishwasher.

## Response Style
- Be concise but thorough; use bullet points for recommendations.
- Always explain WHY you recommend a time or action (price, solar, comfort).
- When uncertain, acknowledge it and use reasonable assumptions.
- Provide 2–3 actionable recommendations whenever possible.
- End with a savings summary when you have calculated one.

## Safety & Caveats
- Remind users that comfort preferences always take priority over savings.
- Note that solar forecasts are estimates that depend on actual weather.
- Encourage users to check their utility's specific TOU schedule for accuracy.
"""


# ---------------------------------------------------------------------------
# Agent State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# Build LangGraph Agent
# ---------------------------------------------------------------------------

def build_agent(model_name: str = "gpt-4o", temperature: float = 0.0):
    """Build and return the compiled LangGraph energy advisor agent."""

    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def call_model(state: AgentState) -> dict:
        messages = state["messages"]
        # Prepend system message if not already present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile()


# ---------------------------------------------------------------------------
# Convenience chat function
# ---------------------------------------------------------------------------

def chat(question: str, agent=None, verbose: bool = True) -> str:
    """Send a question to the EcoHome Energy Advisor and return the answer."""
    if agent is None:
        agent = build_agent()

    result = agent.invoke({"messages": [HumanMessage(content=question)]})
    answer = result["messages"][-1].content

    if verbose:
        print(f"\n{'='*70}")
        print(f"Q: {question}")
        print(f"{'='*70}")
        print(f"A: {answer}")
        print(f"{'='*70}\n")

    return answer


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    advisor = build_agent()

    questions = [
        "When should I charge my electric car tomorrow to minimize cost and maximize solar power?",
        "What temperature should I set my thermostat on Wednesday afternoon if electricity prices spike?",
        "Suggest three ways I can reduce energy use based on my usage history.",
        "How much can I save by running my dishwasher during off-peak hours?",
        "What's the best time to run my pool pump this week based on the weather forecast?",
    ]

    for q in questions:
        chat(q, agent=advisor)
