from __future__ import annotations

from dataclasses import dataclass, field

from app.config import (
    MAX_CONTEXT_CHARS,
    MAX_SOURCES,
    ENABLE_ANSWER_VERIFICATION,
)

from app.scraper import WebScraper
from app.chunker import chunk_documents
from app.embeddings import Embedder
from app.vector_store import VectorStore
from app.retriever import Retriever
from app.llm import LLMClient, FALLBACK_ANSWER
from app.models import RetrievedChunk


# ============================================================
# INGEST RESULT
# ============================================================

@dataclass
class IngestResult:

    pages_crawled: int

    chunks_created: int

    chunks_stored: int

    scope_prefix: str


# ============================================================
# ASK RESULT
# ============================================================

@dataclass
class AskResult:

    answer: str

    sources: list[dict] = field(
        default_factory=list
    )

    chunks_used: int = 0

    verification_note: str | None = None

    # ========================================================
    # RAGAS
    # Stores the actual retrieved chunk text.
    # Ragas will use this as "retrieved_contexts".
    # ========================================================

    retrieved_contexts: list[str] = field(
        default_factory=list
    )


# ============================================================
# RAG PIPELINE
# ============================================================

class RAGPipeline:

    def __init__(self) -> None:

        self.scraper = (
            WebScraper()
        )

        self.embedder = (
            Embedder()
        )

        self.vector_store = (
            VectorStore()
        )

        self.retriever = (
            Retriever(
                embedder=self.embedder,
                vector_store=self.vector_store,
            )
        )

        self.llm = (
            LLMClient()
        )


    # ========================================================
    # INGEST
    # ========================================================

    def ingest(
        self,
        start_url: str,
        reset: bool = True,
    ) -> IngestResult:

        if reset:

            self.vector_store.reset()


        print()
        print("=" * 80)
        print("STARTING WEBSITE INGESTION")
        print("=" * 80)

        print(
            f"START URL: {start_url}"
        )


        # ----------------------------------------------------
        # Crawl
        # ----------------------------------------------------

        documents = (
            self.scraper.crawl(
                start_url
            )
        )


        print()
        print(
            f"Pages crawled: "
            f"{len(documents)}"
        )


        # ----------------------------------------------------
        # Chunk
        # ----------------------------------------------------

        chunks = (
            chunk_documents(
                documents
            )
        )


        print(
            f"Chunks created: "
            f"{len(chunks)}"
        )


        # ----------------------------------------------------
        # Embeddings
        # ----------------------------------------------------

        if not chunks:

            return IngestResult(
                pages_crawled=len(
                    documents
                ),
                chunks_created=0,
                chunks_stored=0,
                scope_prefix=(
                    self.scraper
                    .get_scope_prefix(
                        start_url
                    )
                ),
            )


        print()
        print(
            f"Embedding "
            f"{len(chunks)} chunks..."
        )


        embeddings = (
            self.embedder
            .embed_documents(
                [
                    chunk.content
                    for chunk in chunks
                ]
            )
        )


        # ----------------------------------------------------
        # Store
        # ----------------------------------------------------

        stored = (
            self.vector_store
            .add_documents(
                chunks,
                embeddings,
            )
        )


        print()
        print(
            f"Vectors stored: "
            f"{stored}"
        )

        print("=" * 80)


        return IngestResult(

            pages_crawled=len(
                documents
            ),

            chunks_created=len(
                chunks
            ),

            chunks_stored=stored,

            scope_prefix=(
                self.scraper
                .get_scope_prefix(
                    start_url
                )
            ),
        )


    # ========================================================
    # BUILD CONTEXT
    # ========================================================

    @staticmethod
    def _build_context(
        chunks: list[RetrievedChunk],
    ) -> str:

        parts = []

        total_length = 0


        for chunk in chunks:

            url = (
                chunk.metadata
                .get(
                    "url",
                    "unknown",
                )
            )

            title = (
                chunk.metadata
                .get(
                    "title",
                    "",
                )
            )


            header = (
                f"[SOURCE: "
                f"{title or url}]\n"
                f"URL: {url}\n"
            )


            block = (
                f"{header}"
                f"{chunk.content}\n"
            )


            if (
                total_length
                + len(block)
                > MAX_CONTEXT_CHARS
            ):

                remaining = (
                    MAX_CONTEXT_CHARS
                    - total_length
                )


                if remaining > 200:

                    parts.append(
                        block[:remaining]
                    )

                break


            parts.append(
                block
            )

            total_length += (
                len(block)
            )


        return "\n---\n".join(
            parts
        )


    # ========================================================
    # BUILD SOURCES
    # ========================================================

    @staticmethod
    def _build_sources(
        chunks: list[RetrievedChunk],
    ) -> list[dict]:

        seen = {}


        for chunk in chunks:

            url = (
                chunk.metadata
                .get(
                    "url",
                    "",
                )
            )


            if (
                not url
                or url in seen
            ):
                continue


            seen[url] = {

                "url": url,

                "title": (
                    chunk.metadata
                    .get(
                        "title",
                        "",
                    )
                ),

                "score": round(
                    chunk.hybrid_score,
                    3,
                ),
            }


            if (
                len(seen)
                >= MAX_SOURCES
            ):
                break


        return list(
            seen.values()
        )


    # ========================================================
    # VERIFY
    # ========================================================

    def _verify_answer(
        self,
        answer: str,
        context: str,
    ) -> str | None:

        if (
            not ENABLE_ANSWER_VERIFICATION
            or answer == FALLBACK_ANSWER
        ):
            return None


        prompt = (

            "You are a strict fact checker.\n\n"

            "Given SOURCE EVIDENCE and a DRAFT ANSWER, "
            "reply with exactly one word:\n\n"

            "SUPPORTED\n"
            "or\n"
            "UNSUPPORTED\n\n"

            "SOURCE EVIDENCE:\n"
            f"{context}\n\n"

            "DRAFT ANSWER:\n"
            f"{answer}"
        )


        verdict = (
            self.llm
            .generate(
                question="",
                context=prompt,
            )
            .strip()
            .upper()
        )


        if verdict.startswith(
            "UNSUPPORTED"
        ):

            return (
                "Note: part of this answer "
                "could not be fully verified "
                "against the crawled source."
            )


        return None


    # ========================================================
    # ASK
    # ========================================================

    def ask(
        self,
        question: str,
    ) -> AskResult:

        # ----------------------------------------------------
        # Validate question
        # ----------------------------------------------------

        question = question.strip()

        if not question:

            raise ValueError(
                "Question cannot be empty."
            )


        # ----------------------------------------------------
        # RETRIEVE
        # ----------------------------------------------------

        chunks = (
            self.retriever
            .retrieve(
                question
            )
        )


        # ----------------------------------------------------
        # NO RETRIEVED CHUNKS
        # ----------------------------------------------------

        if not chunks:

            return AskResult(
                answer=FALLBACK_ANSWER,
                sources=[],
                chunks_used=0,
                retrieved_contexts=[],
            )


        # ----------------------------------------------------
        # BUILD RAG CONTEXT
        # ----------------------------------------------------

        context = (
            self._build_context(
                chunks
            )
        )


        # ----------------------------------------------------
        # GENERATE ANSWER
        # ----------------------------------------------------

        answer = (
            self.llm
            .generate(
                question,
                context,
            )
        )


        # ----------------------------------------------------
        # VERIFY ANSWER
        # ----------------------------------------------------

        note = (
            self._verify_answer(
                answer,
                context,
            )
        )


        # ====================================================
        # RAGAS
        # ====================================================
        #
        # IMPORTANT:
        #
        # Ragas needs the actual text returned by the
        # retriever.
        #
        # We therefore expose every retrieved chunk's
        # content here.
        #
        # This does NOT change retrieval.
        # This does NOT change the answer.
        # This does NOT change the Streamlit application.
        #
        # It simply makes the retrieved contexts available
        # for evaluation.
        # ====================================================

        retrieved_contexts = [

            chunk.content

            for chunk in chunks

            if (
                chunk.content
                and chunk.content.strip()
            )
        ]


        # ----------------------------------------------------
        # RETURN RESULT
        # ----------------------------------------------------

        return AskResult(

            answer=answer,

            sources=(
                self._build_sources(
                    chunks
                )
            ),

            chunks_used=len(
                chunks
            ),

            verification_note=note,

            # RAGAS
            retrieved_contexts=(
                retrieved_contexts
            ),
        )