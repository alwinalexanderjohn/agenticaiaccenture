"""
Removes slides 29-34, then regenerates them matching the original deck theme.
Original theme colours:
  White     FFFFFF  — slide titles
  Teal      10B981  — section headings / badges
  LightTeal A7F3D0  — subtitles / slide numbers
  DkTeal    064E3B  — card headings
  BodyText  374151  — body text
  Blue      1D4ED8  — QA node
  Purple    7C3AED  — Summarization node
  Cyan      0891B2  — LangGraph / routing
  Amber     D97706  — Calculator / tools
  Red       DC2626  — Calculation node

Run: python fix_slides_29_34.py
"""

from lxml import etree
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX_PATH = "Document_Assistant.pptx"

# ── Colours matching original deck ────────────────────────────────────────────
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
TEAL    = RGBColor(0x10, 0xB9, 0x81)   # primary accent (green)
LTEAL   = RGBColor(0xA7, 0xF3, 0xD0)   # light teal / subtitle
DKTEAL  = RGBColor(0x06, 0x4E, 0x3B)   # dark teal card headings
BODY    = RGBColor(0x37, 0x41, 0x51)   # body text (dark grey)
BLUE    = RGBColor(0x1D, 0x4E, 0xD8)
PURPLE  = RGBColor(0x7C, 0x3A, 0xED)
CYAN    = RGBColor(0x08, 0x91, 0xB2)
AMBER   = RGBColor(0xD9, 0x77, 0x06)
RED     = RGBColor(0xDC, 0x26, 0x26)
DARK_BG = RGBColor(0x1E, 0x1E, 0x2E)   # dark slide bg (same as 21-28)
CARD_BG = RGBColor(0x0F, 0x17, 0x2A)   # code / card backgrounds
CODE_FG = RGBColor(0xA7, 0xF3, 0xD0)   # code text (light teal on dark)
ROW_ALT = RGBColor(0x16, 0x24, 0x3E)   # alternating table row


# ── Delete the last N slides ───────────────────────────────────────────────────
def delete_last_n_slides(prs, n):
    xml_slides = prs.slides._sldIdLst
    slide_list = list(xml_slides)
    for el in slide_list[-n:]:
        # get rId using the correct namespace
        rId = el.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        if rId:
            try:
                prs.part.drop_rel(rId)
            except Exception:
                pass
        xml_slides.remove(el)


# ── Blank slide factory ────────────────────────────────────────────────────────
def new_slide(prs):
    layout = prs.slide_layouts[0]
    slide  = prs.slides.add_slide(layout)
    for ph in list(slide.placeholders):
        ph._element.getparent().remove(ph._element)
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = DARK_BG
    return slide


# ── Shape helpers ──────────────────────────────────────────────────────────────
def rect(slide, left, top, width, height, fill=CARD_BG, border=None):
    sh = slide.shapes.add_shape(1, left, top, width, height)
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if border:
        sh.line.color.rgb = border
        sh.line.width = Pt(0.75)
    else:
        sh.line.fill.background()
    return sh


def tb(slide, text, left, top, width, height,
       size=Pt(10), colour=WHITE, bold=False, mono=False,
       align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf  = txb.text_frame
    tf.word_wrap = wrap
    first = True
    for line in text.split("\n"):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size  = size
        r.font.bold  = bold
        r.font.color.rgb = colour
        if mono:
            r.font.name = "Courier New"


def slide_title(slide, text, page_num=None):
    """White bold title + optional teal page number."""
    tb(slide, text,
       Inches(0.35), Inches(0.15), Inches(8.8), Inches(0.52),
       size=Pt(18), colour=WHITE, bold=True)
    if page_num:
        tb(slide, page_num,
           Inches(9.1), Inches(0.18), Inches(0.6), Inches(0.35),
           size=Pt(9), colour=LTEAL, align=PP_ALIGN.RIGHT)
    # teal divider line
    ln = slide.shapes.add_shape(1, Inches(0.35), Inches(0.72), Inches(9.3), Inches(0.025))
    ln.fill.solid(); ln.fill.fore_color.rgb = TEAL; ln.line.fill.background()


def code_block(slide, code, left, top, width, height, size=Pt(9)):
    rect(slide, left, top, width, height, fill=CARD_BG)
    txb = slide.shapes.add_textbox(
        left + Inches(0.12), top + Inches(0.1),
        width - Inches(0.24), height - Inches(0.18))
    tf = txb.text_frame; tf.word_wrap = True
    first = True
    for line in code.split("\n"):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        r = p.add_run(); r.text = line
        r.font.size = size; r.font.name = "Courier New"
        r.font.color.rgb = CODE_FG


# ══════════════════════════════════════════════════════════════════════════════
# Slide 29 — AgentState full field table
# ══════════════════════════════════════════════════════════════════════════════
def make_slide_29(prs):
    slide = new_slide(prs)
    slide_title(slide, "AgentState — All 11 Fields  (agent.py)", "29/34")

    fields = [
        ("user_input",            "str",               "—",              "Current user message text"),
        ("messages",              "List[BaseMessage]", "add_messages",   "Full conversation history (append-only)"),
        ("intent",                "UserIntent|None",   "—",              "Classified intent from classify_intent"),
        ("next_step",             "str",               "—",              "Target node name for routing"),
        ("conversation_summary",  "str",               "—",              "LLM-generated rolling summary"),
        ("active_documents",      "List[str]",         "—",              "Document IDs referenced across turns"),
        ("current_response",      "Pydantic|None",     "—",              "Structured output from active agent"),
        ("tools_used",            "List[str]",         "—",              "Tool names called this turn"),
        ("session_id",            "str",               "—",              "LangGraph thread_id for checkpointing"),
        ("user_id",               "str",               "—",              "User identifier"),
        ("actions_taken",         "List[str]",         "operator.add",   "Node names accumulated across turn"),
    ]

    # Header
    hx = [Inches(0.32), Inches(2.22), Inches(3.62), Inches(5.22)]
    hw = [Inches(1.85), Inches(1.35), Inches(1.55), Inches(4.42)]
    headers = ["Field", "Type", "Reducer", "Purpose"]
    hcols   = [TEAL,    TEAL,   TEAL,      TEAL]
    hy = Inches(0.80)
    for text, lft, wid, col in zip(headers, hx, hw, hcols):
        tb(slide, text, lft, hy, wid, Inches(0.28), size=Pt(10), colour=col, bold=True)

    # Rows
    sy = Inches(1.1); rh = Inches(0.52)
    rcols = [LTEAL, AMBER, TEAL, WHITE]
    for i, (f, t, r, p) in enumerate(fields):
        y = sy + i * rh
        if i % 2 == 0:
            rect(slide, Inches(0.3), y, Inches(9.45), rh - Inches(0.02), fill=ROW_ALT)
        for text, lft, wid, col in zip([f, t, r, p], hx, hw, rcols):
            tb(slide, text, lft, y + Inches(0.08), wid, rh - Inches(0.12),
               size=Pt(9.5), colour=col,
               bold=(col in (LTEAL, AMBER)))


# ══════════════════════════════════════════════════════════════════════════════
# Slide 30 — Reducers
# ══════════════════════════════════════════════════════════════════════════════
def make_slide_30(prs):
    slide = new_slide(prs)
    slide_title(slide, "AgentState — Reducers & InMemorySaver", "30/34")

    code = """\
# Default (no reducer) — last write wins — values get overwritten
state["next_step"] = "qa_agent"      # classify_intent sets this
state["next_step"] = "update_memory" # next node overwrites ← data lost!


# add_messages — appends, never overwrites (conversation history)
messages: Annotated[List[BaseMessage], add_messages]
# Turn 1: [HumanMsg("Q1 revenue?"), AIMsg("$4.2M")]
# Turn 2: [HumanMsg("Q2 revenue?"), AIMsg("$5.1M")]
# State : all 4 messages preserved across both turns  ✓


# operator.add — list concatenation across all nodes in one turn
actions_taken: Annotated[List[str], operator.add]
# classify_intent  returns → ["classify_intent"]
# qa_agent         returns → ["qa_agent"]
# update_memory    returns → ["update_memory"]
# Final state              → ["classify_intent", "qa_agent", "update_memory"]  ✓


# InMemorySaver — checkpoints full AgentState after every node
workflow.compile(checkpointer=InMemorySaver())
# Next .invoke() with same thread_id → full state restored
# → true multi-turn memory without a database  ✓"""

    code_block(slide, code, Inches(0.35), Inches(0.82), Inches(9.3), Inches(5.9), size=Pt(9))


# ══════════════════════════════════════════════════════════════════════════════
# Slide 31 — Tools listing
# ══════════════════════════════════════════════════════════════════════════════
def make_slide_31(prs):
    slide = new_slide(prs)
    slide_title(slide, "Tools — calculator & document_reader  (tools.py)", "31/34")

    tb(slide, "🧮  calculator", Inches(0.35), Inches(0.82),
       Inches(9.2), Inches(0.32), size=Pt(12), colour=AMBER, bold=True)

    calc = """\
@tool  def calculator(expression: str) -> str:
  1. Strip commas:     "4,200,000 + 5,100,000"  →  "4200000 + 5100000"
  2. Regex whitelist:  only  digits  + - * / ( ) . %  allowed
  3. Sandboxed eval(): eval(expr, {"__builtins__": {}}, {})
  4. Format result:    int-valued float → "9,300,000"
  5. Log to session:   logs/<session_id>.log  status = OK | INVALID_INPUT | ZERO_DIV | ERROR
  Returns: "Result: 9,300,000  (expression: 4200000 + 5100000)" """

    code_block(slide, calc, Inches(0.35), Inches(1.18), Inches(9.3), Inches(1.7), size=Pt(9))

    tb(slide, "📄  document_reader", Inches(0.35), Inches(2.95),
       Inches(9.2), Inches(0.32), size=Pt(12), colour=CYAN, bold=True)

    dr = """\
@tool  def document_reader(query: str) -> str:
  Path 1  LIST         query="list"              → all doc IDs + titles       status=LIST
  Path 2  EXACT_MATCH  query="doc_financial_q2"  → full document content      status=EXACT_MATCH
  Path 3  KEYWORD      query="revenue growth"    → keyword scored (top 3)     status=KEYWORD_MATCH
  Path 4  FALLBACK     no match found            → first 2 docs in store      status=FALLBACK_ALL
  Path 5  NO_MATCH     store is empty            → "No documents found"        status=NO_MATCH
  All paths append to logs/<session_id>.log with full input + output (no truncation)"""

    code_block(slide, dr, Inches(0.35), Inches(3.3), Inches(9.3), Inches(1.75), size=Pt(9))

    tb(slide,
       "set_session_context(session_id) wires ToolLogger to the correct log file.\n"
       "Both tools are bound to the LLM via llm.bind_tools() and called inside _run_tool_loop().",
       Inches(0.35), Inches(5.12), Inches(9.3), Inches(0.55),
       size=Pt(9.5), colour=LTEAL)


# ══════════════════════════════════════════════════════════════════════════════
# Slide 32 — Tool calling loop
# ══════════════════════════════════════════════════════════════════════════════
def make_slide_32(prs):
    slide = new_slide(prs)
    slide_title(slide, "Tool Calling Loop — _run_tool_loop()  (agent.py)", "32/34")

    code = """\
def _run_tool_loop(llm_with_tools, tool_map, messages, max_iter=5):
    # max_iter=8 for calculation_agent (needs doc_reader + calculator in sequence)
    tools_used, context_snippets = [], []

    for _ in range(max_iter):
        response = llm_with_tools.invoke(messages)   # LLM call
        messages.append(response)

        if not response.tool_calls:                   # LLM done — no more tools
            break

        for tc in response.tool_calls:
            name   = tc["name"]                       # e.g. "document_reader"
            result = tool_map[name].invoke(tc["args"])# runs the tool → logs to file
            tools_used.append(name)
            context_snippets.append(str(result))
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    return messages, tools_used, context_snippets


# After the loop — fallback if LLM never called any tool
if not context_snippets:
    context_snippets = _direct_retrieve(state["user_input"])
    # Searches retriever directly + logs FALLBACK entry to session log


# Phase 2 — structured output call (always after the tool loop)
final_response = llm.with_structured_output(AnswerResponse).invoke(final_prompt)
# final_prompt contains the retrieved content + original question"""

    code_block(slide, code, Inches(0.35), Inches(0.82), Inches(9.3), Inches(5.9), size=Pt(9))


# ══════════════════════════════════════════════════════════════════════════════
# Slide 33 — All 5 agent nodes
# ══════════════════════════════════════════════════════════════════════════════
def make_slide_33(prs):
    slide = new_slide(prs)
    slide_title(slide, "All 5 Agent Nodes — Role & Output  (agent.py)", "33/34")

    nodes = [
        ("1", "classify_intent",     TEAL,
         "When: Entry point — every message\n"
         "Does: llm.with_structured_output(UserIntent) with enriched intent prompt + last 6 messages\n"
         "Out:  intent_type, confidence, reasoning → sets next_step for routing"),

        ("2", "qa_agent",            BLUE,
         "When: intent_type == 'qa'\n"
         "Does: Tool loop → document_reader → Phase 2 with AnswerResponse schema\n"
         "Out:  AnswerResponse(question, answer, sources, confidence, timestamp)"),

        ("3", "summarization_agent", PURPLE,
         "When: intent_type == 'summarization'\n"
         "Does: Tool loop → document_reader → Phase 2 with SummarizationResponse\n"
         "Out:  SummarizationResponse(summary, key_points[3-7], sources, timestamp)"),

        ("4", "calculation_agent",   AMBER,
         "When: intent_type == 'calculation'\n"
         "Does: Tool loop (max 8) — document_reader then calculator → CalculationResponse\n"
         "Out:  CalculationResponse(question, result, expression, sources, timestamp)"),

        ("5", "update_memory",       RED,
         "When: After any specialist agent — always the last node before END\n"
         "Does: LLM writes 1-2 sentence summary; tracks active_documents from sources\n"
         "Out:  conversation_summary and active_documents updated in state"),
    ]

    sy = Inches(0.82); bh = Inches(1.05)
    for num, name, colour, desc in nodes:
        y = sy + (int(num)-1) * bh
        rect(slide, Inches(0.3), y, Inches(9.45), bh - Inches(0.05),
             fill=CARD_BG, border=colour)

        # badge
        b = slide.shapes.add_shape(1, Inches(0.38), y + Inches(0.3),
                                    Inches(0.26), Inches(0.26))
        b.fill.solid(); b.fill.fore_color.rgb = colour; b.line.fill.background()
        tb(slide, num, Inches(0.38), y + Inches(0.28), Inches(0.26), Inches(0.28),
           size=Pt(9), colour=DARK_BG, bold=True, align=PP_ALIGN.CENTER)

        # name
        tb(slide, name, Inches(0.73), y + Inches(0.25),
           Inches(2.1), Inches(0.35), size=Pt(11), colour=colour, bold=True, mono=True)

        # description
        tb(slide, desc, Inches(2.9), y + Inches(0.1),
           Inches(6.75), bh - Inches(0.15), size=Pt(9.5), colour=WHITE)


# ══════════════════════════════════════════════════════════════════════════════
# Slide 34 — Graph routing diagram
# ══════════════════════════════════════════════════════════════════════════════
def make_slide_34(prs):
    slide = new_slide(prs)
    slide_title(slide, "LangGraph Routing — Nodes, Edges & Conditional Flow", "34/34")

    diagram = """\
                   ┌─────────────────────────────────┐
                   │        User sends a message      │
                   └────────────────┬────────────────┘
                                    ▼
                       ┌────────────────────────┐
                       │     classify_intent     │   ← Entry Point
                       │  UserIntent(Pydantic)   │   with_structured_output()
                       └────────────┬───────────┘
                                    │  _route_to_agent(state["next_step"])
          ┌─────────────────────────┼──────────────────────────┐
          │ intent="qa"             │ intent="summarization"    │ intent="calculation"
          ▼                         ▼                           ▼
  ┌───────────────┐    ┌──────────────────────┐    ┌───────────────────────┐
  │   qa_agent    │    │ summarization_agent  │    │  calculation_agent    │
  │ AnswerResponse│    │SummarizationResponse │    │ CalculationResponse   │
  │  tool_loop(5) │    │    tool_loop(5)      │    │    tool_loop(8)       │
  └───────┬───────┘    └──────────┬───────────┘    └───────────┬───────────┘
          │                       │                             │
          └───────────────────────┼─────────────────────────────┘
                                  ▼
                      ┌───────────────────────┐
                      │     update_memory     │   ← Always last node
                      │  summary + doc track  │
                      └──────────┬────────────┘
                                 ▼
                                END
                                         ← InMemorySaver checkpoints state here

Edges added in create_workflow():
  set_entry_point("classify_intent")
  add_conditional_edges("classify_intent", _route_to_agent, {qa/summ/calc})
  add_edge("qa_agent",             "update_memory")
  add_edge("summarization_agent",  "update_memory")
  add_edge("calculation_agent",    "update_memory")
  add_edge("update_memory",        END)"""

    code_block(slide, diagram, Inches(0.35), Inches(0.82), Inches(9.3), Inches(5.92), size=Pt(8.5))


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    prs = Presentation(PPTX_PATH)
    total_before = len(prs.slides)

    # Remove last 6 slides (29-34)
    delete_last_n_slides(prs, 6)
    print(f"Removed 6 slides. Now: {len(prs.slides)}")

    # Re-add with correct theme + compact layout
    make_slide_29(prs)
    make_slide_30(prs)
    make_slide_31(prs)
    make_slide_32(prs)
    make_slide_33(prs)
    make_slide_34(prs)

    prs.save(PPTX_PATH)
    print(f"Saved. Slides: {len(prs.slides)}  (was {total_before})")


if __name__ == "__main__":
    main()
