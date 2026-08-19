from __future__ import annotations

import streamlit as st

from app.config import (
    STREAMLIT_PAGE_TITLE,
    CRAWL_LIMIT,
    OLLAMA_MODEL,
)

from app.rag import RAGPipeline


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title=STREAMLIT_PAGE_TITLE,
    layout="wide",
)


# ============================================================
# PIPELINE
# ============================================================

@st.cache_resource(
    show_spinner=False
)
def get_pipeline() -> RAGPipeline:

    return RAGPipeline()


# ============================================================
# HEADER
# ============================================================

st.title(
    STREAMLIT_PAGE_TITLE
)

st.caption(
    f"Model: {OLLAMA_MODEL} · "
    f"Maximum pages per crawl: {CRAWL_LIMIT}"
)


# ============================================================
# PIPELINE
# ============================================================

with st.spinner(
    "Loading models..."
):

    pipeline = get_pipeline()


# ============================================================
# CHAT MEMORY
# ============================================================

if (
    "messages"
    not in st.session_state
):

    st.session_state.messages = []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "1. Crawl & Index"
    )


    url = st.text_input(
        "Starting URL",

        value="",

        placeholder=(
            "https://kubernetes.io/docs/home/"
        ),
    )


    reset = st.checkbox(
        "Clear existing data first",
        value=True,
    )


    st.info(
        "The crawler starts ONLY from "
        "the URL you enter and follows "
        "in-scope <a href> links recursively. "
        "It does not seed from sitemap.xml."
    )


    if st.button(
        "Crawl & Index",
        type="primary",
        disabled=not url,
    ):

        with st.spinner(
            f"Crawling up to "
            f"{CRAWL_LIMIT} pages..."
        ):

            try:

                result = (
                    pipeline.ingest(
                        url,
                        reset=reset,
                    )
                )


                st.success(
                    f"Indexed "
                    f"{result.pages_crawled} pages "
                    f"and "
                    f"{result.chunks_stored} chunks."
                )


                st.caption(
                    f"Scope: "
                    f"{result.scope_prefix}"
                )


                if (
                    result.pages_crawled
                    < CRAWL_LIMIT
                ):

                    st.warning(
                        f"The crawler reached "
                        f"{result.pages_crawled}/"
                        f"{CRAWL_LIMIT} usable pages. "
                        f"It stopped because the "
                        f"link graph from the supplied "
                        f"starting URL had no more "
                        f"crawlable pages, or the "
                        f"depth/discovery safety "
                        f"limit was reached."
                    )


            except Exception as exc:

                st.error(
                    f"Ingestion failed: {exc}"
                )


    # ========================================================
    # STATUS
    # ========================================================

    st.divider()

    st.header(
        "Status"
    )


    vector_count = (
        pipeline
        .vector_store
        .count()
    )


    st.metric(
        "Chunks indexed",
        vector_count,
    )


    ollama_ok = (
        pipeline
        .llm
        .is_available()
    )


    st.write(
        "Ollama:",
        (
            "🟢 reachable"
            if ollama_ok
            else
            "🔴 not reachable"
        ),
    )


    # ========================================================
    # INDEXED PAGES
    # ========================================================

    urls = (
        pipeline
        .vector_store
        .all_urls()
    )


    if urls:

        with st.expander(
            f"Indexed pages "
            f"({len(urls)})"
        ):

            for index, page_url in enumerate(
                urls,
                start=1,
            ):

                st.write(
                    f"{index}. "
                    f"{page_url}"
                )


# ============================================================
# QUESTION AREA
# ============================================================

st.header(
    "2. Ask Questions"
)


# ============================================================
# PREVIOUS MESSAGES
# ============================================================

for message in (
    st.session_state.messages
):

    with st.chat_message(
        message["role"]
    ):

        st.write(
            message["content"]
        )


        sources = (
            message.get(
                "sources"
            )
        )


        if sources:

            with st.expander(
                "Sources"
            ):

                for source in sources:

                    title = (
                        source.get(
                            "title"
                        )
                        or
                        source.get(
                            "url"
                        )
                    )

                    st.write(
                        f"- {title}"
                    )

                    st.caption(
                        source.get(
                            "url"
                        )
                    )


# ============================================================
# CHAT INPUT
# ============================================================

question = st.chat_input(
    "Ask something about the crawled website..."
)


if question:

    # --------------------------------------------------------
    # User message.
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )


    with st.chat_message(
        "user"
    ):

        st.write(
            question
        )


    # --------------------------------------------------------
    # Assistant.
    # --------------------------------------------------------

    with st.chat_message(
        "assistant"
    ):

        with st.spinner(
            "Retrieving evidence..."
        ):

            result = (
                pipeline.ask(
                    question
                )
            )


        st.write(
            result.answer
        )


        if result.verification_note:

            st.caption(
                result.verification_note
            )


        if result.sources:

            with st.expander(
                "Sources"
            ):

                for source in (
                    result.sources
                ):

                    title = (
                        source.get(
                            "title"
                        )
                        or
                        source.get(
                            "url"
                        )
                    )


                    st.write(
                        f"- {title}"
                    )


                    st.caption(
                        source.get(
                            "url"
                        )
                    )


    # --------------------------------------------------------
    # Save assistant message.
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer,
            "sources": result.sources,
        }
    )