from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from app.config import (
    TOP_K,
    RETRIEVAL_CANDIDATES,
    MIN_SEMANTIC_SCORE,
    MIN_HYBRID_SCORE,
    SEMANTIC_WEIGHT,
    LEXICAL_WEIGHT,
    WHOLE_PAGE_PULL_ENABLED,
    WHOLE_PAGE_PULL_SCORE_MARGIN,
    WHOLE_PAGE_PULL_MAX_CHUNKS,
)

from app.embeddings import Embedder
from app.vector_store import VectorStore
from app.models import RetrievedChunk


# ============================================================
# TOKENIZATION
# ============================================================

_WORD_RE = re.compile(
    r"[a-z0-9]+"
)


# ============================================================
# URL SLUG STOPWORDS
# ============================================================

_STOPWORD_SLUGS = {
    "docs",
    "doc",
    "python",
    "js",
    "api",
    "reference",
    "guide",
    "guides",
    "index",
    "home",
    "www",
    "com",
    "org",
    "io",
    "html",
    "the",
    "page",
}


# ============================================================
# TOKENIZE
# ============================================================

def _tokenize(
    text: str,
) -> list[str]:

    return _WORD_RE.findall(
        text.lower()
    )


# ============================================================
# LEXICAL SCORE
# ============================================================

def _lexical_score(
    query_tokens: Counter,
    doc_text: str,
) -> float:

    if not query_tokens:
        return 0.0

    doc_tokens = Counter(
        _tokenize(doc_text)
    )

    if not doc_tokens:
        return 0.0

    overlap = sum(
        min(
            count,
            doc_tokens.get(
                term,
                0,
            ),
        )

        for term, count
        in query_tokens.items()
    )

    total = sum(
        query_tokens.values()
    )

    if total == 0:
        return 0.0

    return overlap / total


# ============================================================
# URL SLUGS
# ============================================================

def _url_slugs(
    url: str,
) -> set[str]:

    path = urlparse(
        url
    ).path

    slugs = set()

    for segment in path.split("/"):

        segment = (
            segment
            .strip()
            .lower()
            .replace("-", " ")
            .replace("_", " ")
        )

        for word in segment.split():

            if (
                len(word) > 2
                and word
                not in _STOPWORD_SLUGS
            ):

                slugs.add(word)

    return slugs


# ============================================================
# RETRIEVER
# ============================================================

class Retriever:

    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:

        self.embedder = (
            embedder
            or Embedder()
        )

        self.vector_store = (
            vector_store
            or VectorStore()
        )

        self._url_slug_cache = {}


    # ========================================================
    # NAMED PAGE DETECTION
    # ========================================================

    def _named_page_url(
        self,
        question: str,
    ) -> str | None:

        question_tokens = (
            set(
                _tokenize(question)
            )
            - _STOPWORD_SLUGS
        )

        if not question_tokens:
            return None

        urls = (
            self.vector_store
            .all_urls()
        )

        matches = []

        for url in urls:

            if (
                url
                not in self._url_slug_cache
            ):

                self._url_slug_cache[
                    url
                ] = _url_slugs(url)

            slugs = (
                self._url_slug_cache[
                    url
                ]
            )

            if not slugs:
                continue

            matched = (
                question_tokens
                & slugs
            )

            if not matched:
                continue

            specificity = sum(
                len(word)
                for word in matched
            )

            matches.append(
                (
                    specificity,
                    len(matched),
                    url,
                )
            )


        if not matches:
            return None


        matches.sort(
            reverse=True
        )


        best_specificity = (
            matches[0][0]
        )

        best_count = (
            matches[0][1]
        )

        best_url = (
            matches[0][2]
        )


        ties = [
            match
            for match in matches
            if (
                match[0]
                == best_specificity
                and
                match[1]
                == best_count
            )
        ]


        if len(ties) > 1:
            return None


        return best_url


    # ========================================================
    # SCORE CANDIDATES
    # ========================================================

    def _score_candidates(
        self,
        question: str,
    ) -> list[RetrievedChunk]:

        query_embedding = (
            self.embedder
            .embed_query(
                question
            )
        )

        raw = (
            self.vector_store
            .query(
                query_embedding,
                n_results=(
                    RETRIEVAL_CANDIDATES
                ),
            )
        )


        documents = (
            raw.get(
                "documents",
                [[]],
            )[0]
        )

        metadatas = (
            raw.get(
                "metadatas",
                [[]],
            )[0]
        )

        distances = (
            raw.get(
                "distances",
                [[]],
            )[0]
        )


        query_tokens = Counter(
            _tokenize(question)
        )


        scored = []


        for (
            doc_text,
            metadata,
            distance,
        ) in zip(
            documents,
            metadatas,
            distances,
        ):

            semantic_score = max(
                0.0,
                1.0 - float(distance),
            )


            lexical_score = (
                _lexical_score(
                    query_tokens,
                    doc_text,
                )
            )


            hybrid_score = (
                SEMANTIC_WEIGHT
                * semantic_score
            ) + (
                LEXICAL_WEIGHT
                * lexical_score
            )


            scored.append(
                RetrievedChunk(
                    content=doc_text,
                    metadata=metadata,
                    semantic_score=semantic_score,
                    lexical_score=lexical_score,
                    hybrid_score=hybrid_score,
                )
            )


        scored.sort(
            key=lambda chunk:
                chunk.hybrid_score,
            reverse=True,
        )


        return scored


    # ========================================================
    # WHOLE PAGE
    # ========================================================

    def _get_whole_page(
        self,
        url: str,
        semantic_score: float,
        lexical_score: float,
        hybrid_score: float,
    ) -> list[RetrievedChunk]:

        page_data = (
            self.vector_store
            .get_by_url(url)
        )


        page_docs = (
            page_data.get(
                "documents",
                [],
            )
        )

        page_metas = (
            page_data.get(
                "metadatas",
                [],
            )
        )


        if not page_docs:
            return []


        paired = sorted(
            zip(
                page_docs,
                page_metas,
            ),
            key=lambda pair:
                pair[1].get(
                    "chunk_index",
                    0,
                ),
        )


        paired = paired[
            :WHOLE_PAGE_PULL_MAX_CHUNKS
        ]


        return [
            RetrievedChunk(
                content=doc_text,
                metadata=metadata,
                semantic_score=semantic_score,
                lexical_score=lexical_score,
                hybrid_score=hybrid_score,
            )

            for (
                doc_text,
                metadata,
            )
            in paired
        ]


    # ========================================================
    # RETRIEVE
    # ========================================================

    def retrieve(
        self,
        question: str,
    ) -> list[RetrievedChunk]:

        # ----------------------------------------------------
        # 1. Named page retrieval.
        # ----------------------------------------------------

        named_url = (
            self._named_page_url(
                question
            )
        )


        if named_url:

            page_chunks = (
                self._get_whole_page(
                    named_url,
                    1.0,
                    1.0,
                    1.0,
                )
            )

            if page_chunks:

                print(
                    "[RETRIEVAL] "
                    "Named page locked: "
                    f"{named_url}"
                )

                return page_chunks


        # ----------------------------------------------------
        # 2. Normal hybrid retrieval.
        # ----------------------------------------------------

        candidates = (
            self._score_candidates(
                question
            )
        )


        # ----------------------------------------------------
        # Fail closed.
        # ----------------------------------------------------

        filtered = [

            chunk

            for chunk in candidates

            if (
                chunk.semantic_score
                >= MIN_SEMANTIC_SCORE
            )

            and

            (
                chunk.hybrid_score
                >= MIN_HYBRID_SCORE
            )
        ]


        if not filtered:
            return []


        top = filtered[
            :TOP_K
        ]


        # ----------------------------------------------------
        # Whole-page pull.
        # ----------------------------------------------------

        if (
            WHOLE_PAGE_PULL_ENABLED
            and top
        ):

            best = top[0]

            best_url = (
                best.metadata
                .get("url")
            )


            runner_up_score = 0.0


            for chunk in top[1:]:

                chunk_url = (
                    chunk.metadata
                    .get("url")
                )

                if (
                    chunk_url
                    != best_url
                ):

                    runner_up_score = (
                        chunk.hybrid_score
                    )

                    break


            score_margin = (
                best.hybrid_score
                - runner_up_score
            )


            if (
                best_url
                and
                score_margin
                >= WHOLE_PAGE_PULL_SCORE_MARGIN
            ):

                whole_page_chunks = (
                    self._get_whole_page(
                        best_url,
                        best.semantic_score,
                        best.lexical_score,
                        best.hybrid_score,
                    )
                )


                if whole_page_chunks:

                    print(
                        "[RETRIEVAL] "
                        "Whole-page pull: "
                        f"{best_url}"
                    )

                    return whole_page_chunks


        # ----------------------------------------------------
        # Normal top-K.
        # ----------------------------------------------------

        return top