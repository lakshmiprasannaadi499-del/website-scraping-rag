from __future__ import annotations

import re
from urllib.parse import urlparse

import streamlit as st

from app.config import (
    STREAMLIT_PAGE_TITLE,
    CRAWL_LIMIT,
    OLLAMA_MODEL,
)
from app.rag import RAGPipeline


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=STREAMLIT_PAGE_TITLE,
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PROFESSIONAL UI STYLING
# ============================================================

st.markdown(
    """
    <style>
    /* ---------- Global ---------- */
    .stApp {
        background:
            radial-gradient(circle at 85% 0%, #eff6ff 0, #ffffff 28%),
            #ffffff;
        color: #0f172a;
    }

    .main .block-container {
        max-width: 1380px;
        padding: 2rem 2.5rem 4rem;
    }

    #MainMenu,
    footer {
        visibility: hidden;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1.25rem;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #0f172a;
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    .brand-icon {
        width: 36px;
        height: 36px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        background: linear-gradient(135deg, #2563eb, #0ea5e9);
        color: white;
        box-shadow: 0 5px 16px rgba(37, 99, 235, 0.22);
    }

    .sidebar-subtitle {
        color: #64748b;
        font-size: 0.78rem;
        line-height: 1.5;
        margin: 0.55rem 0 1.5rem 46px;
    }

    .sidebar-heading {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #1e293b;
        font-size: 0.92rem;
        font-weight: 750;
        margin: 1rem 0 0.65rem;
    }

    .sidebar-help {
        color: #64748b;
        font-size: 0.82rem;
        line-height: 1.55;
        margin-bottom: 0.8rem;
    }

    /* ---------- Hero ---------- */
    .hero {
        padding: 0.4rem 0 1.5rem;
    }

    .hero-title {
        display: flex;
        align-items: center;
        gap: 12px;
        color: #0f172a;
        font-size: 2.65rem;
        font-weight: 850;
        line-height: 1.1;
        letter-spacing: -0.045em;
        margin-bottom: 0.65rem;
    }

    .hero-icon {
        width: 52px;
        height: 52px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 15px;
        background: linear-gradient(135deg, #2563eb, #06b6d4);
        color: white;
        font-size: 1.75rem;
        box-shadow: 0 10px 28px rgba(37, 99, 235, 0.20);
    }

    .hero-subtitle {
        color: #334155;
        font-size: 1.18rem;
        font-weight: 650;
        margin-bottom: 0.35rem;
    }

    .hero-description {
        max-width: 850px;
        color: #64748b;
        font-size: 0.95rem;
        line-height: 1.65;
    }

    /* ---------- Section headings ---------- */
    .section-title {
        display: flex;
        align-items: center;
        gap: 9px;
        color: #0f172a;
        font-size: 1.35rem;
        font-weight: 800;
        margin: 1.5rem 0 0.85rem;
        letter-spacing: -0.02em;
    }

    .section-description {
        color: #64748b;
        font-size: 0.9rem;
        margin: -0.35rem 0 1rem;
    }

    /* ---------- Metric cards ---------- */
    .metric-card {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1rem 1.1rem;
        min-height: 112px;
        box-shadow: 0 6px 22px rgba(15, 23, 42, 0.045);
    }

    .metric-icon {
        font-size: 1.2rem;
        margin-bottom: 0.45rem;
    }

    .metric-label {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: 0.045em;
    }

    .metric-value {
        color: #0f172a;
        font-size: 1.9rem;
        font-weight: 800;
        line-height: 1.15;
        margin-top: 0.25rem;
    }

    /* ---------- Website status ---------- */
    .status-card {
        background: #ffffff;
        border: 1px solid #dbeafe;
        border-radius: 16px;
        padding: 1rem 1.15rem;
        box-shadow: 0 6px 22px rgba(15, 23, 42, 0.045);
    }

    .status-label {
        color: #64748b;
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }

    .status-name {
        color: #0f172a;
        font-size: 1.05rem;
        font-weight: 800;
    }

    .status-url {
        color: #64748b;
        font-size: 0.78rem;
        margin-top: 0.25rem;
        word-break: break-all;
    }

    .success-card {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 16px;
        padding: 1rem 1.15rem;
        min-height: 86px;
    }

    .success-title {
        color: #166534;
        font-weight: 800;
        font-size: 0.92rem;
    }

    .success-text {
        color: #15803d;
        font-size: 0.78rem;
        margin-top: 0.25rem;
    }

    /* ---------- Configuration cards ---------- */
    .config-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1rem 1.05rem;
        min-height: 105px;
    }

    .config-top {
        display: flex;
        align-items: center;
        gap: 9px;
        color: #334155;
        font-size: 0.82rem;
        font-weight: 750;
        margin-bottom: 0.55rem;
    }

    .config-value {
        color: #0f172a;
        font-size: 0.95rem;
        font-weight: 750;
        word-break: break-word;
    }

    .config-value.mono {
        font-family: "SFMono-Regular", Consolas, monospace;
        color: #2563eb;
    }

    /* ---------- Chat ---------- */
    .question-card {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 14px;
        padding: 0.95rem 1.05rem;
        color: #1e40af;
        line-height: 1.55;
    }

    .answer-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        color: #334155;
        line-height: 1.7;
        box-shadow: 0 5px 18px rgba(15, 23, 42, 0.035);
    }

    .message-label {
        color: #475569;
        font-size: 0.82rem;
        font-weight: 750;
        margin: 0.75rem 0 0.4rem;
    }

    /* ---------- Native Streamlit controls ---------- */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        border: 1px solid #dbe3ee !important;
        transition: all 0.15s ease !important;
    }

    .stButton > button:hover {
        border-color: #2563eb !important;
        box-shadow: 0 5px 16px rgba(37, 99, 235, 0.12) !important;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 10px !important;
        border: 1px solid #cbd5e1 !important;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 1px #2563eb !important;
    }

    div[data-testid="stMetric"] {
        background: transparent;
    }

    /* Make expanders look like clean dashboard panels */
    div[data-testid="stExpander"] {
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        background: #ffffff !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def get_site_name(url: str) -> str:
    """Return a friendly website name instead of exposing HTML."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        parts = [part for part in host.split(".") if part]

        if not parts:
            return "Website"

        name = parts[-2] if len(parts) >= 2 else parts[0]
        name = re.sub(r"[-_]+", " ", name).strip().title()

        if "docs" in parsed.path.lower():
            return f"{name} Documentation"

        return name
    except Exception:
        return "Website"


def get_page_name(url: str, index: int) -> str:
    """Create a readable page label for indexed URLs."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            return f"{get_site_name(url)} Home"

        last_part = path.split("/")[-1]
        last_part = re.sub(r"[-_]+", " ", last_part)
        last_part = re.sub(r"\.(html?|php)$", "", last_part, flags=re.I)

        if not last_part.strip():
            return f"Page {index}"

        return last_part.strip().title()
    except Exception:
        return f"Page {index}"


def render_metric(icon: str, label: str, value: int) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_config(icon: str, label: str, value: object, mono: bool = False) -> None:
    value_class = "config-value mono" if mono else "config-value"
    st.markdown(
        f"""
        <div class="config-card">
            <div class="config-top">
                <span>{icon}</span>
                <span>{label}</span>
            </div>
            <div class="{value_class}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PIPELINE
# ============================================================

@st.cache_resource(show_spinner=False)
def get_pipeline() -> RAGPipeline:
    return RAGPipeline()


with st.spinner("Loading RAG models..."):
    pipeline = get_pipeline()


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_ingestion" not in st.session_state:
    st.session_state.last_ingestion = None

if "indexed_url" not in st.session_state:
    st.session_state.indexed_url = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div class="brand">
            <span class="brand-icon">🌐</span>
            <span>WebRAG Studio</span>
        </div>
        <div class="sidebar-subtitle">
            Website Scraping · RAG · Semantic Search · Local LLM
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(
        """
        <div class="sidebar-heading">
            <span>🔗</span>
            <span>Website Ingestion</span>
        </div>
        <div class="sidebar-help">
            Enter a website URL to crawl its pages and build
            a searchable knowledge base.
        </div>
        """,
        unsafe_allow_html=True,
    )

    url = st.text_input(
        "Website URL",
        value=st.session_state.indexed_url or "",
        placeholder="https://kubernetes.io/docs/home/",
        label_visibility="visible",
    )

    reset = st.checkbox(
        "Clear existing data first",
        value=True,
    )

    if st.button(
        "🚀  Crawl & Index Website",
        type="primary",
        use_container_width=True,
        disabled=not url.strip(),
    ):
        with st.spinner(f"Crawling up to {CRAWL_LIMIT} pages..."):
            try:
                result = pipeline.ingest(
                    url.strip(),
                    reset=reset,
                )

                st.session_state.last_ingestion = result
                st.session_state.indexed_url = url.strip()

                st.success(
                    f"Indexed {result.pages_crawled} pages "
                    f"and {result.chunks_stored} chunks."
                )

                if result.pages_crawled < CRAWL_LIMIT:
                    st.warning(
                        f"The crawler reached "
                        f"{result.pages_crawled}/{CRAWL_LIMIT} usable pages. "
                        "It stopped because the link graph from the supplied "
                        "starting URL had no more crawlable pages, or the "
                        "depth/discovery safety limit was reached."
                    )

            except Exception as exc:
                st.error(f"Ingestion failed: {exc}")

    st.divider()

    st.markdown(
        """
        <div class="sidebar-heading">
            <span>⚙️</span>
            <span>RAG Pipeline</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vector_count = pipeline.vector_store.count()

    st.metric(
        "🧠 Vectors Stored",
        vector_count,
    )

    ollama_ok = pipeline.llm.is_available()

    st.write(
        "Ollama:",
        "🟢 Reachable" if ollama_ok else "🔴 Not reachable",
    )

    st.caption(f"Local model: {OLLAMA_MODEL}")


# ============================================================
# MAIN HERO
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">
            <span class="hero-icon">🌐</span>
            <span>WebRAG Studio</span>
        </div>
        <div class="hero-subtitle">
            Website Scraping & Retrieval-Augmented Question Answering
        </div>
        <div class="hero-description">
            Crawl a website, create searchable chunks, generate embeddings,
            store them in a vector database, and ask questions using a
            local LLM.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CURRENT INDEX INFORMATION
# ============================================================

urls = pipeline.vector_store.all_urls()


# ============================================================
# INGESTION DASHBOARD
# ============================================================

st.markdown(
    """
    <div class="section-title">
        <span>📊</span>
        <span>Ingestion Dashboard</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.last_ingestion:
    pages_crawled = st.session_state.last_ingestion.pages_crawled
    chunks_created = st.session_state.last_ingestion.chunks_stored
else:
    pages_crawled = len(urls)
    chunks_created = vector_count

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    render_metric("🌐", "Pages Crawled", pages_crawled)

with metric_col2:
    render_metric("✂️", "Chunks Created", chunks_created)

with metric_col3:
    render_metric("🧠", "Vectors Stored", vector_count)

with metric_col4:
    render_metric("🗄️", "Database Vectors", vector_count)


# ============================================================
# INDEXED WEBSITE STATUS
# ============================================================

indexed_url = st.session_state.indexed_url or (urls[0] if urls else None)

if indexed_url:
    st.markdown(
        """
        <div class="section-title">
            <span>🔎</span>
            <span>Current Knowledge Base</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    status_col1, status_col2 = st.columns([2.6, 1])

    with status_col1:
        site_name = get_site_name(indexed_url)

        st.markdown(
            f"""
            <div class="status-card">
                <div class="status-label">🌐 Indexed Website</div>
                <div class="status-name">{site_name}</div>
                <div class="status-url">{indexed_url}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.link_button(
            f"🔗  Open {site_name}",
            indexed_url,
            use_container_width=False,
        )

    with status_col2:
        st.markdown(
            """
            <div class="success-card">
                <div class="success-title">✓ Indexed Successfully</div>
                <div class="success-text">
                    Website content is ready for semantic search.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# EMBEDDING & INDEXING DETAILS
# ============================================================

st.write("")

with st.expander("🧠  Embedding & Indexing Details", expanded=True):

    embedding_model = getattr(
        pipeline,
        "embedding_model",
        "BAAI/bge-small-en-v1.5",
    )

    chunk_overlap = getattr(
        pipeline,
        "chunk_overlap",
        120,
    )

    chunk_size = getattr(
        pipeline,
        "chunk_size",
        900,
    )

    retrieval_top_k = getattr(
        pipeline,
        "top_k",
        getattr(
            pipeline,
            "retrieval_top_k",
            6,
        ),
    )

    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:
        render_config(
            "🧠",
            "Embedding Model",
            embedding_model,
            mono=True,
        )

        st.write("")

        render_config(
            "📦",
            "Chunk Size",
            chunk_size,
            mono=True,
        )

    with detail_col2:
        render_config(
            "↔️",
            "Chunk Overlap",
            chunk_overlap,
            mono=True,
        )

        st.write("")

        render_config(
            "🎯",
            "Retrieval Top-K",
            retrieval_top_k,
            mono=True,
        )


# ============================================================
# INDEXED PAGES
# ============================================================

if urls:
    with st.expander(f"📚  Indexed Pages · {len(urls)}"):

        st.caption(
            "Select a page to open the original website. "
            "Only the page name is displayed — no raw HTML is shown."
        )

        page_cols = st.columns(2)

        for index, page_url in enumerate(urls, start=1):
            page_name = get_page_name(page_url, index)

            with page_cols[(index - 1) % 2]:
                st.link_button(
                    f"📄  {page_name}",
                    page_url,
                    use_container_width=True,
                )


# ============================================================
# ASK YOUR WEBSITE
# ============================================================

st.markdown(
    """
    <div class="section-title">
        <span>💬</span>
        <span>Ask Your Website</span>
    </div>
    <div class="section-description">
        Ask questions about content that has been indexed into
        the RAG knowledge base.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PREVIOUS MESSAGES
# ============================================================

for message in st.session_state.messages:

    role = message["role"]

    if role == "user":

        st.markdown(
            '<div class="message-label">❓ Your Question</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="question-card">{message["content"]}</div>',
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            '<div class="message-label">🤖 AI Answer</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="answer-card">{message["content"]}</div>',
            unsafe_allow_html=True,
        )

        sources = message.get("sources")

        if sources:
            with st.expander("🔗  Sources"):

                for index, source in enumerate(sources, start=1):

                    title = (
                        source.get("title")
                        or source.get("url")
                        or f"Source {index}"
                    )

                    source_url = source.get("url")

                    if source_url:
                        st.link_button(
                            f"🔗  {title}",
                            source_url,
                            use_container_width=False,
                        )
                    else:
                        st.write(f"• {title}")


# ============================================================
# QUESTION INPUT
# ============================================================

question = st.text_input(
    "Your Question",
    placeholder="Ask something about the crawled website...",
    label_visibility="visible",
    key="website_question",
)


# ============================================================
# ASK BUTTON
# ============================================================

ask_button = st.button(
    "🔍  Ask Website",
    type="primary",
    use_container_width=True,
    disabled=not question.strip(),
)


# ============================================================
# QUESTION PROCESSING
# ============================================================

if ask_button and question.strip():

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question.strip(),
        }
    )

    with st.spinner("Retrieving evidence and generating answer..."):

        try:
            result = pipeline.ask(question.strip())

        except Exception as exc:
            st.error(f"Question answering failed: {exc}")
            st.stop()

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer,
            "sources": result.sources,
        }
    )

    st.rerun()
