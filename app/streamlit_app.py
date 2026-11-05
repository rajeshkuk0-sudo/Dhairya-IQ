import html
import pathlib
import sys

import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.ids import query_id
from src.config.loader import load_config

st.set_page_config(
    page_title="Dhairya-IQ",
    layout="wide",
    initial_sidebar_state="expanded",
)
cfg = load_config()

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:ital,wght@0,300..900;1,300..900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

:root {
  --primary: #006c4f;
  --primary-container: #00d09c;
  --on-primary-container: #00533c;
  --secondary-container: #99efe5;
  --on-secondary-container: #006f67;
  --surface: #faf8ff;
  --surface-low: #f2f3ff;
  --surface-container: #eaedff;
  --surface-high: #e2e7ff;
  --on-surface: #131b2e;
  --on-surface-variant: #3c4a43;
  --outline: #6b7b72;
  --outline-variant: #bacac1;
  --answer-bg: #032e22;
  --answer-fg: #2fe0aa;
}

html, body, [class*="css"], .stApp, button, input, textarea {
  font-family: 'Hanken Grotesk', sans-serif;
}
.stApp, [data-testid="stAppViewContainer"] {
  background: var(--surface);
  color: var(--on-surface);
}
[data-testid="stHeader"] { background: transparent; }
.block-container {
  max-width: 1040px;
  padding-top: 1.5rem;
  padding-bottom: 9rem;
}
a { color: var(--primary); }

[data-testid="stSidebar"] {
  background: #ffffff;
  border-right: 1px solid var(--surface-container);
  width: 288px;
  min-width: 288px;
}
[data-testid="stSidebarContent"] {
  padding: 0.15rem 0.85rem 1rem !important;
}
[data-testid="stSidebarHeader"] {
  height: 1.75rem;
  min-height: 1.75rem;
  margin: 0;
  padding: 0;
}
[data-testid="stSidebarUserContent"] {
  padding-top: 0.1rem;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.2rem; }
[data-testid="stSidebar"] .stButton > button {
  width: 100%;
  justify-content: flex-start;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 8px;
  color: var(--on-surface);
  font-size: 12px;
  font-weight: 600;
  padding: 0.35rem 0.5rem;
  min-height: 2rem;
  box-shadow: none;
}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stButton > button:focus {
  background: var(--surface-low) !important;
  color: var(--primary) !important;
  border: 0;
  box-shadow: none;
}
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button div {
  text-align: left !important;
  justify-content: flex-start !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] details {
  border: 0 !important;
  background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  padding: 0.3rem 0.35rem !important;
  border-radius: 8px;
  color: var(--outline) !important;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
  background: var(--surface-low) !important;
  color: var(--primary) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
  padding: 0.15rem 0 0 !important;
}

.side-brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  border-bottom: 1px solid var(--surface-container);
  padding-bottom: 0.9rem;
  margin-bottom: 0.65rem;
}
.brand-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--primary-container);
  color: var(--on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-icon .material-symbols-outlined { font-size: 20px; }
.brand-name {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  color: var(--on-surface);
}
.brand-sub {
  font-size: 11px;
  font-weight: 600;
  color: var(--primary);
}
.side-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--outline);
  margin: 0.7rem 0 1rem;
  padding: 0 0.35rem 0.2rem;
}
.side-footer {
  background: var(--surface-low);
  border-top: 1px solid var(--surface-container);
  border-radius: 10px;
  padding: 0.8rem;
  margin-top: 1rem;
}
.side-footer .row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}
.side-footer .avatar {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: var(--primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.side-footer .avatar .material-symbols-outlined { font-size: 17px; }
.side-footer .title { font-size: 12px; font-weight: 700; line-height: 1.1; }
.side-footer .sub { font-size: 11px; font-weight: 600; color: var(--primary); }
.side-footer p {
  margin: 0.35rem 0 0;
  font-size: 11px;
  line-height: 1.35;
  color: var(--outline);
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  background: rgba(242, 243, 255, 0.75);
  border-radius: 999px;
  padding: 0.35rem 0.75rem;
  margin-bottom: 1.35rem;
}
.status-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  color: var(--on-surface-variant);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.status-left .material-symbols-outlined { font-size: 16px; color: var(--primary); }
.status-badge {
  background: rgba(0, 208, 156, 0.18);
  color: var(--on-primary-container);
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 11px;
  font-weight: 700;
}

.welcome-card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.04);
  padding: 1.35rem;
  margin-bottom: 1.2rem;
}
.welcome-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.welcome-title-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.2rem;
}
.welcome-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: var(--primary-container);
  color: var(--on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}
.welcome-icon .material-symbols-outlined { font-size: 20px; }
.welcome-title-row h1 {
  margin: 0;
  font-size: 22px;
  line-height: 30px;
  font-weight: 700;
  color: var(--on-surface);
}
.welcome-card p {
  margin: 0.25rem 0 0;
  max-width: 760px;
  font-size: 14px;
  line-height: 22px;
  color: var(--on-surface-variant);
}
.verified-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: var(--secondary-container);
  color: var(--on-secondary-container);
  border-radius: 999px;
  padding: 0.25rem 0.6rem;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}
.verified-pill .material-symbols-outlined { font-size: 14px; }
.examples-label {
  margin: 0.9rem 0 0.4rem;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--outline);
}

main#stMain [data-testid="stBaseButton-secondary"] {
  width: 100%;
  justify-content: flex-start;
  text-align: left;
  white-space: normal;
  min-height: 2.6rem;
  height: auto;
  background: var(--surface-low) !important;
  border: 1px solid var(--outline-variant) !important;
  border-radius: 999px !important;
  color: var(--on-surface) !important;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  padding: 0.5rem 0.9rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}
main#stMain [data-testid="stBaseButton-secondary"] p,
main#stMain [data-testid="stBaseButton-secondary"] span {
  color: var(--on-surface) !important;
  text-align: left !important;
}
main#stMain [data-testid="stBaseButton-secondary"] div[class*="stMarkdownEllipsis"] {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
}
main#stMain [data-testid="stBaseButton-secondary"]:hover,
main#stMain [data-testid="stBaseButton-secondary"]:focus {
  background: var(--surface-container) !important;
  border-color: var(--outline-variant) !important;
  color: var(--primary) !important;
}
main#stMain [data-testid="stBaseButton-secondary"]:hover p,
main#stMain [data-testid="stBaseButton-secondary"]:focus p,
main#stMain [data-testid="stBaseButton-secondary"]:hover span,
main#stMain [data-testid="stBaseButton-secondary"]:focus span {
  color: var(--primary) !important;
}

.thread-question {
  margin: 1.1rem 0 0.5rem;
  font-size: 18px;
  line-height: 26px;
  font-weight: 600;
  color: var(--on-surface);
}
.thread-you { font-weight: 700; margin-right: 0.4rem; }
.answer-card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.04);
  padding: 1rem;
  margin-bottom: 1rem;
}
.assistant-head {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.8rem;
}
.assistant-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: var(--primary-container);
  color: var(--on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}
.assistant-icon .material-symbols-outlined { font-size: 21px; }
.assistant-name {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}
.assistant-sub {
  font-size: 11px;
  font-weight: 600;
  color: var(--outline);
  margin-top: 0.15rem;
}
.answer-bubble {
  border-radius: 12px;
  background: var(--answer-bg);
  color: var(--answer-fg);
  padding: 1rem 1.2rem;
  font-size: 18px;
  line-height: 1.5;
  font-weight: 500;
}
.refusal-bubble {
  border-radius: 12px;
  background: var(--surface-low);
  color: var(--on-surface);
  padding: 0.9rem 1.1rem;
  font-size: 16px;
  line-height: 1.5;
}
.answer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  border-top: 1px solid var(--surface-low);
  margin-top: 0.75rem;
  padding-top: 0.6rem;
  font-size: 11px;
  color: var(--outline);
}
.answer-meta .source {
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface);
}
.answer-meta a {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  text-decoration: underline;
  overflow-wrap: anywhere;
}
.privacy-notice {
  background: rgba(153, 239, 229, 0.4);
  color: var(--on-secondary-container);
  border-radius: 10px;
  padding: 0.55rem 0.75rem;
  margin-bottom: 0.75rem;
  font-size: 12px;
  font-weight: 600;
}
.refusal-card { border-left: 4px solid var(--outline); }

[data-testid="stChatInput"] {
  background: #ffffff !important;
  border: 1px solid var(--outline-variant);
  border-radius: 16px;
  box-shadow: 0 8px 30px rgba(19, 27, 46, 0.10);
  padding: 0.35rem;
}
[data-testid="stChatInput"] > div {
  background: #ffffff !important;
}
[data-testid="stChatInputTextArea"] {
  background: #ffffff !important;
  color: var(--on-surface) !important;
  caret-color: var(--primary);
  font-size: 14px;
}
[data-testid="stChatInputTextArea"]::placeholder {
  color: var(--outline) !important;
  opacity: 1 !important;
}
[data-testid="stChatInputSubmitButton"] {
  background: var(--surface-low) !important;
  color: var(--primary) !important;
  border-radius: 8px !important;
}
[data-testid="stChatInputSubmitButton"] svg {
  color: inherit !important;
}
[data-testid="stChatInputSubmitButton"]:hover {
  background: var(--surface-container) !important;
  color: var(--primary) !important;
}
[data-testid="stChatInputSubmitButton"]:disabled {
  background: var(--surface-container) !important;
  color: var(--outline) !important;
  opacity: 1 !important;
}
[data-testid="stBottom"] > div {
  background: linear-gradient(to top, var(--surface) 55%, rgba(250, 248, 255, 0));
}

.side-footer .title { color: var(--on-surface) !important; }
.side-footer .avatar { color: #ffffff !important; }

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

SCHEMES = [
    ("HDFC AMC Overview", "What is the overview of HDFC Mutual Fund?"),
    (
        "HDFC Large Cap Fund",
        "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    ),
    (
        "HDFC Flexi Cap Fund",
        "What is the expense ratio of HDFC Flexi Cap Fund Direct Growth?",
    ),
    (
        "HDFC ELSS Tax Saver",
        "What is the lock-in period for HDFC ELSS Tax Saver?",
    ),
    (
        "HDFC Mid Cap Fund",
        "What is the exit load and minimum SIP for HDFC Mid Cap Fund?",
    ),
]
TOPICS = [
    ("Expense Ratios · TER", "What is the expense ratio of HDFC Flexi Cap Fund?"),
    ("Exit Load · Redemption", "What is the exit load for HDFC Flexi Cap Fund?"),
    ("Minimum SIP · Lumpsum", "What is the minimum SIP for HDFC Flexi Cap Fund?"),
    ("ELSS Lock-in · Sec 80C", "What is the lock-in period for HDFC ELSS Tax Saver?"),
    (
        "Riskometer · Benchmark",
        "What are the riskometer and benchmark for HDFC Flexi Cap Fund?",
    ),
    ("Statement Download", "How do I download my capital gains statement?"),
]


def icon(name: str) -> str:
    return f'<span class="material-symbols-outlined">{name}</span>'


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


@st.cache_resource
def orch():
    from src.orchestration.query_orchestrator import QueryOrchestrator

    return QueryOrchestrator(cfg)


with st.sidebar:
    st.markdown(
        f"""
        <div class="side-brand">
          <div class="brand-icon">{icon("account_balance")}</div>
          <div>
            <div class="brand-name">{esc(cfg.ui.title)}</div>
            <div class="brand-sub">Your FAQ Assistant</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar.expander(f"Supported Schemes ({len(SCHEMES)})", expanded=False):
        for index, (label, prompt) in enumerate(SCHEMES):
            if st.button(label, key=f"scheme_{index}", use_container_width=True):
                st.session_state.pending = prompt

    st.markdown('<div class="side-label">FAQ Quick Topics</div>', unsafe_allow_html=True)
    for index, (label, prompt) in enumerate(TOPICS):
        if st.button(label, key=f"topic_{index}", use_container_width=True):
            st.session_state.pending = prompt

    st.markdown(
        f"""
        <div class="side-footer">
          <div class="row">
            <div class="avatar">{icon("verified_user")}</div>
            <div>
              <div class="title">Statutory Notice</div>
              <div class="sub">Facts-Only Policy</div>
            </div>
          </div>
          <p>Public official Groww/AMC pages only. No advice, no portfolio claims, zero PII.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    f"""
    <div class="status-bar">
      <div class="status-left">
        {icon("shield")}
        <span>HDFC Mutual Fund Scheme Facts &amp; FAQ Assistant (5 HDFC Schemes)</span>
      </div>
      <span class="status-badge">Facts-only · No investment advice · 1 Official Source per answer</span>
    </div>

    <div class="welcome-card">
      <div class="welcome-head">
        <div>
          <div class="welcome-title-row">
            <div class="welcome-icon">{icon("search_insights")}</div>
            <h1>Welcome to Your Mutual Fund Facts Assistant</h1>
          </div>
          <p>Ask factual queries about expense ratios, exit loads, minimum SIP, lock-in periods, or statement guides for the supported HDFC schemes.</p>
        </div>
        <span class="verified-pill">{icon("verified")} Facts-only. No investment advice.</span>
      </div>
      <div class="examples-label">Try example inquiries</div>
    </div>
    """,
    unsafe_allow_html=True,
)

example_columns = st.columns(2)
for index, example in enumerate(cfg.ui.example_questions):
    with example_columns[index % 2]:
        if st.button(example, key=f"example_{index}", use_container_width=True):
            st.session_state.pending = example

typed = st.chat_input(
    "Ask facts about HDFC schemes (expense ratio, exit load, SIP, ELSS lock-in)..."
)
question = st.session_state.pop("pending", None) or typed

if question:
    with st.spinner("Searching official sources..."):
        try:
            result = orch().ask(question)
        except Exception:
            result = None
            st.session_state.qid = query_id(question)
            st.error("Could not complete the lookup. Check that the index is built.")
    if result:
        st.session_state.qid = result["query_id"]
        st.session_state.setdefault("history", []).append(result)

history = st.session_state.get("history", [])

for result in history:
    st.markdown(
        f'<div class="thread-question"><span class="thread-you">You:</span> {esc(result["query"])}</div>',
        unsafe_allow_html=True,
    )
    refused = bool(result.get("refused"))
    card_class = "answer-card refusal-card" if refused else "answer-card"
    bubble_class = "refusal-bubble" if refused else "answer-bubble"

    if result.get("mode") == "guardrail":
        title = "Policy Refusal Notice (Facts-Only)"
        sub = "Dhairya-IQ Assistant · Guardrail"
    elif result.get("mode") == "not_found":
        title = "Source Coverage Notice"
        sub = "Dhairya-IQ Assistant · No matching official source"
    elif refused:
        title = "Verification Notice"
        sub = "Dhairya-IQ Assistant · Answer not verified"
    else:
        title = "Dhairya-IQ Assistant"
        sub = "Official source verified · Facts-only"

    notice = (
        f'<div class="privacy-notice">{esc(result["notice"])}</div>'
        if result.get("notice")
        else ""
    )
    citation = result.get("citation") or ""
    source = (
        f'<a href="{esc(citation)}" target="_blank" rel="noopener noreferrer">{esc(citation)}</a>'
        if citation
        else ""
    )
    updated = (
        f'<span>Last updated from sources: {esc(result["last_updated"])}</span>'
        if result.get("last_updated")
        else ""
    )

    st.markdown(
        f"""
        <div class="{card_class}">
          <div class="assistant-head">
            <div class="assistant-icon">{icon("psychology")}</div>
            <div>
              <div class="assistant-name">{esc(title)}</div>
              <div class="assistant-sub">{esc(sub)}</div>
            </div>
          </div>
          {notice}
          <div class="{bubble_class}">{esc(result["answer"]).replace(chr(10), "<br>")}</div>
          <div class="answer-meta">
            <div><span class="source">Source:</span> {source}</div>
            {updated}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

