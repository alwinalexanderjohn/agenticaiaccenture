"""
Appends updated slides to Document_Assistant.pptx covering all recent changes.
Run: python update_pptx.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX_PATH = "Document_Assistant.pptx"

# ── Colour palette ─────────────────────────────────────────────────────────────
DARK_BG   = RGBColor(0x1E, 0x1E, 0x2E)   # dark navy
ACCENT    = RGBColor(0x74, 0xC7, 0xEC)   # sky blue
GREEN     = RGBColor(0xA6, 0xE3, 0xA1)   # green
YELLOW    = RGBColor(0xF9, 0xE2, 0xAF)   # yellow
RED       = RGBColor(0xF3, 0x8B, 0xA8)   # red/pink
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT     = RGBColor(0xCD, 0xD6, 0xF4)   # light lavender


def _bg(slide, prs):
    """Fill slide background with dark colour."""
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = DARK_BG


def _title_box(slide, text, top=Inches(0.25)):
    txb = slide.shapes.add_textbox(Inches(0.4), top, Inches(9.2), Inches(0.65))
    tf  = txb.text_frame
    p   = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = text
    run.font.bold  = True
    run.font.size  = Pt(24)
    run.font.color.rgb = ACCENT


def _body_box(slide, text, left=Inches(0.4), top=Inches(1.1),
              width=Inches(9.2), height=Inches(5.8),
              size=Pt(13), colour=WHITE, bold=False, mono=False):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf  = txb.text_frame
    tf.word_wrap = True
    first = True
    for line in text.split("\n"):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = line
        run.font.size  = size
        run.font.bold  = bold
        run.font.color.rgb = colour
        if mono:
            run.font.name = "Courier New"


def _code_box(slide, code, left=Inches(0.4), top=Inches(1.1),
              width=Inches(9.2), height=Inches(5.5)):
    """Dark code block."""
    # Background rectangle
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0x18, 0x18, 0x2E)
    shape.line.fill.background()

    txb = slide.shapes.add_textbox(
        left + Inches(0.1), top + Inches(0.1),
        width - Inches(0.2), height - Inches(0.2)
    )
    tf = txb.text_frame
    tf.word_wrap = True
    first = True
    for line in code.split("\n"):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        run = p.add_run()
        run.text = line
        run.font.size = Pt(11)
        run.font.name = "Courier New"
        run.font.color.rgb = GREEN


def add_slide(prs, layout_idx=0):
    layout = prs.slide_layouts[layout_idx]
    slide  = prs.slides.add_slide(layout)
    # Remove all placeholder shapes that came with the layout
    for ph in slide.placeholders:
        sp = ph._element
        sp.getparent().remove(sp)
    _bg(slide, prs)
    return slide


# ── Build slides ───────────────────────────────────────────────────────────────

def slide_section_divider(prs, title, subtitle):
    slide = add_slide(prs)
    txb = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1.2))
    tf  = txb.text_frame
    p   = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = title
    run.font.bold  = True
    run.font.size  = Pt(32)
    run.font.color.rgb = ACCENT

    txb2 = slide.shapes.add_textbox(Inches(1), Inches(3.8), Inches(8), Inches(0.7))
    tf2  = txb2.text_frame
    p2   = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = subtitle
    run2.font.size  = Pt(16)
    run2.font.color.rgb = LIGHT


def slide_numbered_menu(prs):
    slide = add_slide(prs)
    _title_box(slide, "Update 1 — Numbered Menu CLI (main.py)")

    desc = (
        "Replaced free-text command input with a numbered menu.\n"
        "Every option shows a repeat-or-back sub-menu after each action.\n"
    )
    _body_box(slide, desc, top=Inches(1.0), height=Inches(0.7), colour=LIGHT, size=Pt(13))

    menu = """\
  ┌─────────────────────────────────────────┐
  │  1  📁  Upload Document                 │
  │  2  ❓  Question & Answer               │
  │  3  📄  Summarize Document              │
  │  4  🧮  Calculator                      │
  │  5  📚  Show Loaded Documents           │
  │  6  ℹ️   Session Info                   │
  │  0  ❌  Quit                            │
  └─────────────────────────────────────────┘

  After each action:
  ┌──────────────────────────────────────────┐
  │  1  🔄  Ask another question             │
  │  0  ↩   Back to main menu                │
  └──────────────────────────────────────────┘"""
    _code_box(slide, menu, top=Inches(1.85), height=Inches(4.6))


def slide_tkinter(prs):
    slide = add_slide(prs)
    _title_box(slide, "Update 2 — Native File Picker (tkinter)")

    desc = (
        "Option 1 opens a native Windows file browser dialog via tkinter.filedialog.\n"
        "Falls back to manual path entry if dialog is unavailable.\n"
        "Supports: PDF  TXT  MD  CSV"
    )
    _body_box(slide, desc, top=Inches(1.0), height=Inches(0.9), colour=LIGHT, size=Pt(13))

    code = """\
def _pick_file() -> str | None:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()               # hide blank Tk window
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Select a document to upload",
        filetypes=[
            ("Supported files", "*.pdf *.txt *.md *.csv"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return path if path else None

# Fallback if dialog unavailable:
file_path = input("  Path: ").strip()"""
    _code_box(slide, code, top=Inches(2.0), height=Inches(4.4))


def slide_per_session_logs(prs):
    slide = add_slide(prs)
    _title_box(slide, "Update 3 — Per-Session Logs (tools.py)")

    desc = (
        "OLD: One file per day  →  logs/tool_calls_2026-10-05.log  (no session ID)\n"
        "NEW: One file per session  →  logs/<session_id>.log\n\n"
        "All code paths now logged with status labels:"
    )
    _body_box(slide, desc, top=Inches(1.0), height=Inches(1.1), colour=LIGHT, size=Pt(13))

    code = """\
# tools.py — session context
_current_session_id: str = "unknown"

def set_session_context(session_id: str) -> None:
    global _current_session_id
    _current_session_id = session_id   # called by assistant.start_session()

class ToolLogger:
    @staticmethod
    def log(tool_name, input_data, output, status="OK"):
        log_file = Path("logs") / f"{_current_session_id}.log"
        with open(log_file, "a") as f:
            f.write(f"[{ts}]  Tool: {tool_name}  |  Status: {status}\\n")
            f.write(f"  Input:  {input_data}\\n")
            f.write(f"  Output: {output}\\n\\n")   # no truncation

# Status labels: LIST | EXACT_MATCH | KEYWORD_MATCH | FALLBACK_ALL
#                NO_MATCH | ERROR | INVALID_INPUT | ZERO_DIVISION | FALLBACK"""
    _code_box(slide, code, top=Inches(2.2), height=Inches(4.2))


def slide_session_history(prs):
    slide = add_slide(prs)
    _title_box(slide, "Update 4 — Full Conversation History in sessions/")

    desc = (
        "OLD: sessions/<uuid>.json had only metadata (session_id, user_id, message_count)\n"
        "NEW: Each turn is appended to conversation_history with full detail"
    )
    _body_box(slide, desc, top=Inches(1.0), height=Inches(0.75), colour=LIGHT, size=Pt(13))

    code = """\
{
  "session_id": "c3d4e5f6-calculation-revenue-session",
  "user_id": "user_001",
  "created_at": "2026-10-05T11:20:00",
  "message_count": 3,
  "conversation_history": [
    {
      "turn": 1,
      "timestamp": "2026-10-05T11:20:15",
      "user_input": "Calculate: total revenue Q1 and Q2",
      "intent_type": "calculation",
      "intent_confidence": 0.97,
      "intent_reasoning": "Prefix 'Calculate:' is explicit; adding two revenue figures requires arithmetic.",
      "tools_used": ["document_reader", "calculator"],
      "sources": ["doc_financial_q1", "doc_financial_q2"],
      "response": "Combined revenue is $9,300,000 ...",
      "conversation_summary": "..."
    }
  ]
}"""
    _code_box(slide, code, top=Inches(1.9), height=Inches(4.5))


def slide_messages_placeholder(prs):
    slide = add_slide(prs)
    _title_box(slide, "Update 5 — MessagesPlaceholder in ChatPromptTemplate")

    desc = (
        "All three agent prompt templates now include MessagesPlaceholder\n"
        "so prior conversation turns are visible to the LLM (multi-turn context)."
    )
    _body_box(slide, desc, top=Inches(1.0), height=Inches(0.75), colour=LIGHT, size=Pt(13))

    code = """\
# prompts.py — BEFORE
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

return ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{user_input}"),
])


# prompts.py — AFTER
from langchain_core.prompts import (
    PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
)

return ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="conversation_history", optional=True),
    ("human", "{user_input}"),
])


# agent.py — each agent now passes history into format_messages()
recent_history = state.get("messages", [])[-6:]
messages = prompt_template.format_messages(
    user_input=enriched_input,
    conversation_history=recent_history,
)"""
    _code_box(slide, code, top=Inches(1.9), height=Inches(4.5))


def slide_intent_prompt(prs):
    slide = add_slide(prs)
    _title_box(slide, "Update 6 — Enriched Intent Classification Prompt")

    desc = (
        "Four improvements added to _INTENT_CLASSIFICATION_TEMPLATE in prompts.py:"
    )
    _body_box(slide, desc, top=Inches(1.0), height=Inches(0.5), colour=LIGHT, size=Pt(13))

    content = """\
1. EXAMPLES PER CATEGORY (3 per category)
   "What is the readmission rate?" → qa,  confidence: 0.95
     reasoning: "Direct factual question; no arithmetic required."
   "Summarize the Q2 financial report" → summarization,  confidence: 0.97
     reasoning: "'Summarize' is explicit; user wants condensed content."
   "What is the combined revenue Q1+Q2?" → calculation,  confidence: 0.95
     reasoning: "Requires adding two figures from separate documents."

2. CONFIDENCE SCORING GUIDE
   0.90–1.00  Intent is explicit and unambiguous
   0.70–0.89  Likely correct but one other category is plausible
   0.50–0.69  Genuinely ambiguous; fits two categories equally
   Below 0.50  Very unclear — default to "qa"

3. TIE-BREAKING RULES
   • Any request needing arithmetic → "calculation" (beats "qa")
   • "overview / highlight / tell me about" → "summarization"
   • Follow-up requests → inherit intent from conversation_history
   • Uncertain → "qa" is the safe fallback

4. REASONING INSTRUCTIONS
   "Name the specific words/phrases that drove your choice AND
    explain why you ruled out the next-closest category." """
    _code_box(slide, content, top=Inches(1.6), height=Inches(4.8))


def slide_summary_of_changes(prs):
    slide = add_slide(prs)
    _title_box(slide, "Summary of All Updates")

    rows = [
        ("1", "main.py",    "Numbered menu (1-6) + repeat-or-back sub-menu on every option"),
        ("2", "main.py",    "tkinter native file picker for Upload (Option 1)"),
        ("3", "tools.py",   "Per-session log files: logs/<session_id>.log"),
        ("4", "tools.py",   "All tool paths logged (LIST/EXACT/KEYWORD/FALLBACK/ERROR)"),
        ("5", "agent.py",   "_direct_retrieve() now logs its fallback calls"),
        ("6", "assistant.py","Full conversation history saved to sessions/<uuid>.json"),
        ("7", "prompts.py", "MessagesPlaceholder added to all ChatPromptTemplates"),
        ("8", "prompts.py", "Intent prompt: 3 examples/category, confidence guide, tie-breaking"),
    ]

    top = Inches(1.05)
    row_h = Inches(0.52)
    for i, (num, file, desc) in enumerate(rows):
        y = top + i * row_h
        # Number badge
        badge = slide.shapes.add_shape(1, Inches(0.35), y + Inches(0.05),
                                        Inches(0.35), Inches(0.38))
        badge.fill.solid()
        badge.fill.fore_color.rgb = ACCENT
        badge.line.fill.background()
        tb = slide.shapes.add_textbox(Inches(0.35), y + Inches(0.04),
                                       Inches(0.35), Inches(0.38))
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = num
        r.font.bold = True; r.font.size = Pt(12)
        r.font.color.rgb = DARK_BG

        # File label
        ftb = slide.shapes.add_textbox(Inches(0.8), y, Inches(1.5), Inches(0.5))
        fp = ftb.text_frame.paragraphs[0]
        fr = fp.add_run(); fr.text = file
        fr.font.bold = True; fr.font.size = Pt(12)
        fr.font.color.rgb = YELLOW

        # Description
        dtb = slide.shapes.add_textbox(Inches(2.4), y, Inches(7.0), Inches(0.5))
        dp = dtb.text_frame.paragraphs[0]
        dr = dp.add_run(); dr.text = desc
        dr.font.size = Pt(12); dr.font.color.rgb = WHITE


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    prs = Presentation(PPTX_PATH)

    # Section divider
    slide_section_divider(prs,
        "Recent Updates — Oct 2026",
        "CLI  ·  Logging  ·  Sessions  ·  Prompt Engineering")

    # Individual update slides
    slide_numbered_menu(prs)
    slide_tkinter(prs)
    slide_per_session_logs(prs)
    slide_session_history(prs)
    slide_messages_placeholder(prs)
    slide_intent_prompt(prs)
    slide_summary_of_changes(prs)

    prs.save(PPTX_PATH)
    print(f"Saved {PPTX_PATH}  ({len(prs.slides)} slides total)")


if __name__ == "__main__":
    main()
