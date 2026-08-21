from __future__ import annotations

import re
from urllib.parse import urlparse

import streamlit as st

from app.config import (
    STREAMLIT_PAGE_TITLE,
    CRAWL_LIMIT,
    OPENROUTER_MODEL,
)

from app.rag import RAGPipeline


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=STREAMLIT_PAGE_TITLE,
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PROFESSIONAL NATIVE STREAMLIT THEME
#
# IMPORTANT:
# No HTML is used anywhere in this UI.
# This prevents <div>, <span>, hero-title, etc.
# from appearing as raw text.
# ============================================================

st.markdown(
    """
    <style>

    /* Main background */
    .stApp {
        background-color: #f8fafc;
    }

    /* Main content width */
    .main .block-container {
        max-width: 1380px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* Hide Streamlit footer */
    footer {
        visibility: hidden;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 700;
        min-height: 42px;
    }

    /* Text inputs */
    div[data-testid="stTextInput"] input {
        border-radius: 10px;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        border-radius: 12px;
    }

    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 12px;
    }

    /* Divider */
    hr {
        border-color: #e2e8f0;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def get_site_name(url: str) -> str:
    """
    Return a friendly website name.
    """

    try:
        parsed = urlparse(url)

        host = (
            parsed.netloc
            .lower()
            .replace("www.", "")
        )

        parts = [
            part
            for part in host.split(".")
            if part
        ]

        if not parts:
            return "Website"

        if len(parts) >= 2:
            name = parts[-2]
        else:
            name = parts[0]

        name = re.sub(
            r"[-_]+",
            " ",
            name,
        ).strip().title()

        if "docs" in parsed.path.lower():
            return f"{name} Documentation"

        return name

    except Exception:
        return "Website"


def get_page_name(
    url: str,
    index: int,
) -> str:
    """
    Create a readable page label.
    """

    try:
        parsed = urlparse(url)

        path = parsed.path.strip("/")

        if not path:
            return f"{get_site_name(url)} Home"

        last_part = path.split("/")[-1]

        last_part = re.sub(
            r"[-_]+",
            " ",
            last_part,
        )

        last_part = re.sub(
            r"\.(html?|php)$",
            "",
            last_part,
            flags=re.I,
        )

        last_part = last_part.strip()

        if not last_part:
            return f"Page {index}"

        return last_part.title()

    except Exception:
        return f"Page {index}"


def safe_answer_text(value: object) -> str:
    """
    Convert answer content safely to plain text.

    This prevents accidental raw HTML from the model
    from becoming part of the dashboard UI.
    """

    if value is None:
        return ""

    text = str(value)

    # Remove common HTML tags.
    text = re.sub(
        r"<[^>]+>",
        "",
        text,
    )

    # Convert a few common HTML entities.
    replacements = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new,
        )

    return text.strip()


# ============================================================
# PIPELINE
# ============================================================

@st.cache_resource(show_spinner=False)
def get_pipeline() -> RAGPipeline:
    """
    Create the RAG pipeline once.

    This keeps crawler, embeddings, ChromaDB,
    retrieval and LLM initialization cached.
    """

    return RAGPipeline()


with st.spinner("Loading knowledge assistant..."):
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

# IMPORTANT:
# We use a changing key for the question widget.
# This avoids:
#
# StreamlitAPIException:
# st.session_state.website_question cannot be
# modified after the widget is instantiated.
#
if "question_input_key" not in st.session_state:
    st.session_state.question_input_key = 0


# ============================================================
# CURRENT VECTOR COUNT
# ============================================================

try:
    vector_count = pipeline.vector_store.count()
except Exception:
    vector_count = 0


# ============================================================
# CURRENT URLS
# ============================================================

try:
    urls = pipeline.vector_store.all_urls()
except Exception:
    urls = []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # --------------------------------------------------------
    # BRAND
    # --------------------------------------------------------

    st.markdown(
        "# ◈ KnowledgeFlow"
    )

    st.caption(
        "Website Knowledge Assistant"
    )

    st.divider()

    # --------------------------------------------------------
    # BUILD KNOWLEDGE BASE
    # --------------------------------------------------------

    st.subheader(
        "📚 Build Knowledge Base"
    )

    st.write(
        "Add a documentation website to create "
        "a searchable knowledge base."
    )

    url = st.text_input(
        "Website URL",
        value=(
            st.session_state.indexed_url
            or ""
        ),
        placeholder=(
            "https://docs.example.com/"
        ),
    )

    reset = st.checkbox(
        "Clear existing data first",
        value=True,
    )

    st.caption(
        "The crawler starts from your URL and "
        "follows relevant in-scope links recursively."
    )

    crawl_button = st.button(
        "🚀 Crawl & Index Website",
        type="primary",
        use_container_width=True,
        disabled=not url.strip(),
    )

    if crawl_button and url.strip():

        with st.spinner(
            f"Crawling up to {CRAWL_LIMIT} pages..."
        ):

            try:

                result = pipeline.ingest(
                    url.strip(),
                    reset=reset,
                )

                st.session_state.last_ingestion = result
                st.session_state.indexed_url = (
                    url.strip()
                )

                st.success(
                    f"Indexed "
                    f"{result.pages_crawled} pages "
                    f"and "
                    f"{result.chunks_stored} chunks."
                )

                if (
                    result.pages_crawled
                    < CRAWL_LIMIT
                ):

                    st.info(
                        f"The crawler indexed "
                        f"{result.pages_crawled}/"
                        f"{CRAWL_LIMIT} usable pages."
                    )

                st.rerun()

            except Exception as exc:

                st.error(
                    f"Ingestion failed: {exc}"
                )

    st.divider()

    # --------------------------------------------------------
    # SYSTEM STATUS
    # --------------------------------------------------------

    st.subheader(
        "⚡ System Status"
    )

    st.metric(
        "Indexed Chunks",
        f"{vector_count:,}",
    )

    try:
        openrouter_ok = (
            pipeline.llm.is_available()
        )
    except Exception:
        openrouter_ok = False

    if openrouter_ok:

        st.success(
            "● System Ready"
        )

    else:

        st.warning(
            "● System needs attention"
        )

    st.caption(
        f"AI model: {OPENROUTER_MODEL}"
    )

    st.divider()

    # --------------------------------------------------------
    # RAG PIPELINE
    # --------------------------------------------------------

    st.subheader(
        "⚙️ RAG Pipeline"
    )

    st.metric(
        "Vectors Stored",
        f"{vector_count:,}",
    )

    st.caption(
        "Crawler → Chunking → Embeddings → "
        "ChromaDB → Retrieval → OpenRouter"
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.title(
    "🌐 Ask Your Website"
)

st.subheader(
    "Website Knowledge Assistant"
)

st.write(
    "Crawl website documentation, build a "
    "searchable knowledge base, and get answers "
    "grounded in the content you indexed."
)


# ============================================================
# SYSTEM STATUS
# ============================================================

st.divider()

st.subheader(
    "⚡ System Status"
)

status_col1, status_col2, status_col3 = st.columns(
    3
)

with status_col1:

    st.metric(
        "Indexed Chunks",
        f"{vector_count:,}",
    )

with status_col2:

    st.metric(
        "Indexed Pages",
        f"{len(urls):,}",
    )

with status_col3:

    st.metric(
        "Maximum Crawl Pages",
        f"{CRAWL_LIMIT:,}",
    )


# ============================================================
# SYSTEM READY STATUS
# ============================================================

try:
    openrouter_ok = (
        pipeline.llm.is_available()
    )
except Exception:
    openrouter_ok = False


if openrouter_ok:

    st.success(
        f"✓ System Ready · AI model: {OPENROUTER_MODEL}"
    )

else:

    st.warning(
        f"System is running, but the AI model "
        f"connection could not be verified.\n\n"
        f"Configured model: {OPENROUTER_MODEL}"
    )


# ============================================================
# CURRENT KNOWLEDGE BASE
# ============================================================

st.divider()

st.subheader(
    "📚 Your Knowledge Base"
)

st.caption(
    "Content indexed from your selected website."
)


# ============================================================
# KNOWLEDGE BASE METRICS
# ============================================================

kb_col1, kb_col2, kb_col3 = st.columns(
    3
)

if st.session_state.last_ingestion:

    pages_crawled = (
        st.session_state
        .last_ingestion
        .pages_crawled
    )

    chunks_created = (
        st.session_state
        .last_ingestion
        .chunks_stored
    )

else:

    pages_crawled = len(urls)

    chunks_created = vector_count


with kb_col1:

    st.metric(
        "Indexed Chunks",
        f"{chunks_created:,}",
    )

with kb_col2:

    st.metric(
        "Indexed Pages",
        f"{pages_crawled:,}",
    )

with kb_col3:

    st.metric(
        "Maximum Crawl Pages",
        f"{CRAWL_LIMIT:,}",
    )


# ============================================================
# INDEXED WEBSITE
# ============================================================

indexed_url = (
    st.session_state.indexed_url
    or (
        urls[0]
        if urls
        else None
    )
)

if indexed_url:

    st.divider()

    st.subheader(
        "🌐 Current Knowledge Base"
    )

    site_name = get_site_name(
        indexed_url
    )

    website_col1, website_col2 = st.columns(
        [3, 1]
    )

    with website_col1:

        st.info(
            f"Indexed Website\n\n"
            f"**{site_name}**\n\n"
            f"{indexed_url}"
        )

    with website_col2:

        st.link_button(
            f"🔗 Open {site_name}",
            indexed_url,
        )


# ============================================================
# EMBEDDING & INDEXING DETAILS
# ============================================================

st.divider()

with st.expander(
    "🧠 Embedding & Indexing Details",
    expanded=True,
):

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

    detail_col1, detail_col2 = st.columns(
        2
    )

    with detail_col1:

        st.write(
            "🧠 **Embedding Model**"
        )

        st.code(
            str(embedding_model),
            language="text",
        )

        st.write(
            "📦 **Chunk Size**"
        )

        st.code(
            str(chunk_size),
            language="text",
        )

    with detail_col2:

        st.write(
            "↔️ **Chunk Overlap**"
        )

        st.code(
            str(chunk_overlap),
            language="text",
        )

        st.write(
            "🎯 **Retrieval Top-K**"
        )

        st.code(
            str(retrieval_top_k),
            language="text",
        )


# ============================================================
# INDEXED PAGES
# ============================================================

if urls:

    st.divider()

    with st.expander(
        f"📄 Indexed Pages ({len(urls)})",
        expanded=False,
    ):

        st.caption(
            "Open an indexed page from the original website."
        )

        # Two-column page layout.
        page_columns = st.columns(
            2
        )

        for index, page_url in enumerate(
            urls,
            start=1,
        ):

            page_name = get_page_name(
                page_url,
                index,
            )

            column = page_columns[
                (index - 1) % 2
            ]

            with column:

                st.link_button(
                    f"📄 {page_name}",
                    page_url,
                    use_container_width=True,
                )


# ============================================================
# ASK QUESTIONS
# ============================================================

st.divider()

st.subheader(
    "💬 Ask Questions"
)

st.caption(
    "Ask questions in natural language and get "
    "answers based on your indexed website content."
)


# ============================================================
# PREVIOUS CHAT
# ============================================================

for message in st.session_state.messages:

    role = message.get(
        "role",
        "assistant",
    )

    content = safe_answer_text(
        message.get(
            "content",
            "",
        )
    )

    if role == "user":

        with st.chat_message(
            "user"
        ):

            st.write(
                content
            )

    else:

        with st.chat_message(
            "assistant"
        ):

            st.write(
                content
            )

            sources = message.get(
                "sources"
            )

            if sources:

                with st.expander(
                    "🔗 Sources"
                ):

                    for index, source in enumerate(
                        sources,
                        start=1,
                    ):

                        if not isinstance(
                            source,
                            dict,
                        ):
                            st.write(
                                f"{index}. {source}"
                            )
                            continue

                        title = (
                            source.get(
                                "title"
                            )
                            or source.get(
                                "url"
                            )
                            or f"Source {index}"
                        )

                        source_url = source.get(
                            "url"
                        )

                        if source_url:

                            st.link_button(
                                f"🔗 {title}",
                                source_url,
                            )

                        else:

                            st.write(
                                f"• {title}"
                            )


# ============================================================
# QUESTION INPUT
#
# IMPORTANT:
# DO NOT use:
#
# st.session_state.website_question = ""
#
# after st.text_input().
#
# Instead, use a dynamic widget key.
# ============================================================

question_key = (
    f"website_question_"
    f"{st.session_state.question_input_key}"
)


question = st.text_input(
    "Your Question",
    placeholder=(
        "Ask something about the crawled website..."
    ),
    label_visibility="visible",
    key=question_key,
)


# ============================================================
# ASK BUTTON
# ============================================================

ask_button = st.button(
    "🔍 Ask Website",
    type="primary",
    use_container_width=True,
    disabled=not question.strip(),
)


# ============================================================
# QUESTION PROCESSING
# ============================================================

if (
    ask_button
    and question.strip()
):

    clean_question = (
        question.strip()
    )

    # --------------------------------------------------------
    # Save user question
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": clean_question,
        }
    )

    # --------------------------------------------------------
    # Generate answer
    # --------------------------------------------------------

    with st.spinner(
        "Retrieving evidence and generating answer..."
    ):

        try:

            result = pipeline.ask(
                clean_question
            )

        except Exception as exc:

            st.error(
                f"Question answering failed: {exc}"
            )

            st.stop()

    # --------------------------------------------------------
    # Save assistant answer
    # --------------------------------------------------------

    answer = safe_answer_text(
        getattr(
            result,
            "answer",
            "",
        )
    )

    sources = getattr(
        result,
        "sources",
        [],
    )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Instead of modifying:
    #
    # st.session_state.website_question = ""
    #
    # create a new widget key.
    # --------------------------------------------------------

    st.session_state.question_input_key += 1

    st.rerun()
