# Document Assistant — Multi-Agent AI System

An AI-powered document assistant built with **LangGraph**, **LangChain**, and **OpenAI GPT-4o**. It classifies user intent and routes requests to specialist agents for Q&A, summarization, and calculation tasks.

---

## Architecture

```
User Input
    │
    ▼
DocumentAssistant.process_message()
    │
    ▼
LangGraph StateGraph
    │
    ├── classify_intent  ──► routes based on intent_type
    │        │
    │        ├── "qa"             ──► qa_agent             ──┐
    │        ├── "summarization"  ──► summarization_agent  ──┤
    │        └── "calculation"    ──► calculation_agent    ──┘
    │                                                         │
    └────────────────────────────────────────────────── update_memory ──► END
```

### Multi-Agent Pattern
The system uses the **Router/Dispatcher** pattern: one classifier node routes to specialist agents. No agent knows about routing; the router knows nothing about documents.

---

## Project Structure

```
doc_assistant_project/
├── src/
│   ├── schemas.py      # Pydantic v2 output models
│   ├── agent.py        # LangGraph workflow, AgentState, 5 nodes
│   ├── retrieval.py    # DocumentRetriever (keyword search + PDF support)
│   ├── tools.py        # calculator + document_reader LangChain tools
│   ├── prompts.py      # System prompts + intent classification prompt
│   └── assistant.py    # DocumentAssistant class (session management)
├── streamlit_app.py    # 3-tab Streamlit UI
├── samples/            # 4 sample CSV datasets
├── sessions/           # Auto-generated: one JSON file per session
├── logs/               # Auto-generated: daily tool-call log files
└── requirements.txt
```

---

## State and Memory

### AgentState (TypedDict)
All nodes share a single `AgentState` TypedDict. LangGraph merges node return values into it automatically.

| Field | Type | Reducer | Purpose |
|---|---|---|---|
| `user_input` | `str` | — | Current user message |
| `messages` | `List[BaseMessage]` | `add_messages` | Full conversation history (append-only) |
| `intent` | `UserIntent \| None` | — | Classified intent from router |
| `next_step` | `str` | — | Target node name for routing |
| `conversation_summary` | `str` | — | LLM-generated rolling summary |
| `active_documents` | `List[str]` | — | Doc IDs referenced across turns |
| `current_response` | `Pydantic \| None` | — | Structured output from active agent |
| `tools_used` | `List[str]` | — | Tools called this turn |
| `session_id` | `str` | — | LangGraph `thread_id` for checkpointing |
| `user_id` | `str` | — | User identifier |
| `actions_taken` | `List[str]` | `operator.add` | Node names run this turn (accumulated) |

**Reducers:**
- `add_messages` — appends new messages instead of overwriting (LangGraph built-in)
- `operator.add` — list concatenation, accumulates node names across the turn

### InMemorySaver
The workflow is compiled with `InMemorySaver()` as a checkpointer. After every node, LangGraph saves the full `AgentState` keyed by `thread_id`. On the next `.invoke()` call with the same `thread_id`, state is restored — enabling true multi-turn memory within a session.

### Sessions Directory
`DocumentAssistant` auto-creates a `sessions/` directory. After each message, session metadata (session ID, user ID, message count, timestamp) is written to `sessions/<session_id>.json`.

### Logs Directory
`tools.py` auto-creates a `logs/` directory and writes every tool invocation to `logs/tool_calls_<YYYY-MM-DD>.log` with timestamps, tool name, input, and output.

---

## Structured Output Enforcement

All agent responses use Pydantic v2 models via `llm.with_structured_output(Schema)`. The LLM is forced to conform to the schema — missing or wrong-type fields raise validation errors.

### UserIntent
```python
class UserIntent(BaseModel):
    intent_type: Literal["qa", "summarization", "calculation", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
```
`Literal` restricts `intent_type` to exactly four valid values. Any other string is rejected by Pydantic.

### AnswerResponse
```python
class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]
    confidence: float = Field(ge=0.0, le=1.0)   # enforced 0–1 range
    timestamp: datetime = Field(default_factory=datetime.now)
```

### SummarizationResponse
```python
class SummarizationResponse(BaseModel):
    summary: str
    key_points: List[str]
    sources: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)
```

### CalculationResponse
```python
class CalculationResponse(BaseModel):
    question: str
    result: str
    expression: str
    sources: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)
```

---

## Tools

### `calculator`
- Decorated with `@tool`
- Strips comma separators, then validates input with regex `^[\d\s\+\-\*\/\.\(\)\%]+$`
- Evaluates using `eval()` with empty `__builtins__` (sandboxed)
- Returns a **string** result (e.g. `"Result: 1,900,000 (expression: 1900000)"`)
- Handles `ZeroDivisionError`, unsupported characters, and general exceptions

### `document_reader`
- Decorated with `@tool`
- Tries exact document ID lookup first (`retriever.get_document(query)`)
- Falls back to keyword search (`retriever.search_documents(query)`)
- Returns full document content as a formatted string

---

## Implementation Decisions

1. **Keyword retrieval (not RAG)** — Documents are matched by term-count scoring on full text, not vector embeddings. No embedding API costs; works reliably for structured CSVs.

2. **RunnableConfig for dependency injection** — LLM and tools are NOT global. They are passed per-invocation via `RunnableConfig["configurable"]`. Node functions must type the `config` parameter as `RunnableConfig` (not `dict`) for LangGraph to inject it automatically.

3. **Two-phase agent pattern** — Each specialist agent runs a tool loop first (gather data), then calls `with_structured_output()` (produce typed response). This separates retrieval from response generation.

4. **Per-tab session isolation (Streamlit)** — Each tab owns a separate `DocumentAssistant` instance with its own `thread_id`. The `DocumentRetriever` is a module-level singleton shared across tabs.

5. **Intent hint prefixes** — The Streamlit UI prepends `"Please summarize: "` or `"Calculate: "` to user input when the tab context makes intent clear, improving routing accuracy.

---

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:
```
OPENAI_API_KEY=sk-...
```

Run the Streamlit app:
```bash
streamlit run app.py
```

Or run the CLI assistant:
```bash
python main.py
```

---

## Example Conversations

### Q&A
```
User:  What is the readmission rate in the healthcare report?
Agent: The 30-day readmission rate is 8.3%, as reported in the Healthcare Statistics 2026 document.
       🎯 Confidence: 95%
       📎 Sources: `doc_healthcare_stats`
```

### Summarization
```
User:  Summarize the Q2 financial report
Agent: Q2 2026 saw strong performance with total revenue of $5.1M and net profit of $1.9M.

       Key Points:
       • Total Revenue: $5,100,000 (up from $4.2M in Q1)
       • Net Profit: $1,900,000 with a 67% gross margin
       • Year-over-Year Growth: 31%
       • Customer base expanded to 13,421
       📎 Sources: `doc_financial_q2`
```

### Calculation
```
User:  What is the combined net profit for Q1 and Q2?
Agent: The combined net profit for Q1 and Q2 2026 is $3,300,000.
       Q1 Net Profit ($1,400,000) + Q2 Net Profit ($1,900,000) = $3,300,000

       🧮 Expression: `1400000 + 1900000`
       📎 Sources: `doc_financial_q1`, `doc_financial_q2`
```

---

## Sample Data

| File | Rows | Description |
|---|---|---|
| `finance_transactions_500.csv` | 500 | Transaction records with revenue, COGS, profit |
| `hospital_patient_records_500.csv` | 500 | Patient admissions, costs, outcomes |
| `q3_2026_financial_report.csv` | 27 | Quarterly financial summary |
| `city_hospital_department_stats.csv` | 12 | 10-department hospital performance |
