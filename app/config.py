from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# PATHS
# ============================================================

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"


# ============================================================
# LOAD .ENV
# ============================================================

load_dotenv(ENV_FILE)


# ============================================================
# ENV HELPERS
# ============================================================

def _env_string(name: str, default: str) -> str:
    value = os.getenv(name)

    if value is None:
        return default

    return str(value).strip()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)

    except (TypeError, ValueError):
        print(
            f"[CONFIG WARNING] "
            f"Invalid integer {name}={value!r}. "
            f"Using default={default}."
        )

        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return float(value)

    except (TypeError, ValueError):
        print(
            f"[CONFIG WARNING] "
            f"Invalid float {name}={value!r}. "
            f"Using default={default}."
        )

        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    value = str(value).strip().lower()

    if value in {"1", "true", "yes", "y", "on"}:
        return True

    if value in {"0", "false", "no", "n", "off"}:
        return False

    print(
        f"[CONFIG WARNING] "
        f"Invalid boolean {name}={value!r}. "
        f"Using default={default}."
    )

    return default


# ============================================================
# API KEYS
# ============================================================

FIRECRAWL_API_KEY = _env_string(
    "FIRECRAWL_API_KEY",
    "",
)


# ============================================================
# OLLAMA / LLM
# ============================================================

OLLAMA_HOST = _env_string(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
)

OLLAMA_MODEL = _env_string(
    "OLLAMA_MODEL",
    "qwen3:8b",
)

OLLAMA_CONNECT_TIMEOUT = _env_int(
    "OLLAMA_CONNECT_TIMEOUT",
    20,
)

OLLAMA_TIMEOUT = _env_int(
    "OLLAMA_TIMEOUT",
    600,
)

LLM_TEMPERATURE = _env_float(
    "LLM_TEMPERATURE",
    0.1,
)

LLM_NUM_CTX = _env_int(
    "LLM_NUM_CTX",
    16384,
)

LLM_MAX_TOKENS = _env_int(
    "LLM_MAX_TOKENS",
    1200,
)

ENABLE_ANSWER_VERIFICATION = _env_bool(
    "ENABLE_ANSWER_VERIFICATION",
    True,
)


# ============================================================
# WEBSITE CRAWLING
# ============================================================

# Maximum successfully extracted pages.
CRAWL_LIMIT = _env_int(
    "CRAWL_LIMIT",
    500,
)

# Maximum hyperlink depth.
CRAWL_MAX_DEPTH = _env_int(
    "CRAWL_MAX_DEPTH",
    30,
)

# Compatibility aliases.
CRAWL_DEPTH = CRAWL_MAX_DEPTH
MAX_CRAWL_DEPTH = CRAWL_MAX_DEPTH


# ------------------------------------------------------------
# IMPORTANT
#
# "path" means:
#
# https://kubernetes.io/docs/home/
#
# becomes:
#
# https://kubernetes.io/docs/*
#
# The scraper below calculates this from the FIRST path
# segment of the URL supplied by the user.
# ------------------------------------------------------------

SCOPE_MODE = _env_string(
    "SCOPE_MODE",
    "path",
).lower()


# ------------------------------------------------------------
# We do NOT use external links.
# ------------------------------------------------------------

ALLOW_EXTERNAL_LINKS = _env_bool(
    "ALLOW_EXTERNAL_LINKS",
    False,
)


# ------------------------------------------------------------
# Respect robots.txt.
# ------------------------------------------------------------

IGNORE_ROBOTS_TXT = _env_bool(
    "IGNORE_ROBOTS_TXT",
    False,
)


# ------------------------------------------------------------
# HTTP settings
# ------------------------------------------------------------

CRAWL_TIMEOUT = _env_int(
    "CRAWL_TIMEOUT",
    120,
)

LOCAL_REQUEST_TIMEOUT = _env_int(
    "LOCAL_REQUEST_TIMEOUT",
    20,
)

CRAWL_RETRY_ATTEMPTS = _env_int(
    "CRAWL_RETRY_ATTEMPTS",
    2,
)

CRAWL_REQUEST_DELAY = _env_float(
    "CRAWL_REQUEST_DELAY",
    0.10,
)


# ------------------------------------------------------------
# Link discovery
# ------------------------------------------------------------

MAX_LINKS_PER_PAGE = _env_int(
    "MAX_LINKS_PER_PAGE",
    500,
)


# ------------------------------------------------------------
# Safety limit for discovered URLs.
#
# This is NOT the number of pages to crawl.
# It prevents infinite/crazy link graphs.
# ------------------------------------------------------------

CRAWL_DISCOVERY_LIMIT = _env_int(
    "CRAWL_DISCOVERY_LIMIT",
    10000,
)


# ============================================================
# SITEMAP
# ============================================================

# IMPORTANT:
#
# The requested crawler MUST NOT use sitemap.xml to seed the
# crawl.
#
# We keep these variables only for compatibility with old code.
# The new scraper does not call sitemap discovery.
# ============================================================

USE_SITEMAP_SEED = os.getenv(
    "USE_SITEMAP_SEED",
    "false"
).lower() == "true"

SITEMAP_TIMEOUT = _env_int(
    "SITEMAP_TIMEOUT",
    15,
)

SITEMAP_MAX_URLS = _env_int(
    "SITEMAP_MAX_URLS",
    2000,
)


# ============================================================
# CRAWL FILTERING
# ============================================================

BLOCKED_PATH_KEYWORDS = [
    "/login",
    "/signin",
    "/sign-in",
    "/signup",
    "/sign-up",
    "/register",

    "/cart",
    "/checkout",

    "/jobs",
    "/job",

    "/events",
    "/event",

    "/advertisement",
    "/advertising",
    "/ads",

    "/premium",
    "/subscription",

    "/account",
    "/user",

    "/privacy",
    "/terms",
]


BLOCKED_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".ico",

    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".mkv",

    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",

    ".exe",
    ".dmg",
    ".iso",

    ".woff",
    ".woff2",
    ".ttf",

    ".css",
    ".js",
    ".json",
    ".xml",
]


# ============================================================
# FIRECRAWL
# ============================================================

# Firecrawl is ONLY a content fallback.
#
# It does NOT discover URLs.
# It does NOT seed the crawl.
# The link graph is always discovered from <a href>.
# ============================================================

USE_FIRECRAWL_FALLBACK = _env_bool(
    "USE_FIRECRAWL_FALLBACK",
    False,
)

FIRECRAWL_FORMAT = _env_string(
    "FIRECRAWL_FORMAT",
    "markdown",
)

FIRECRAWL_ONLY_MAIN_CONTENT = _env_bool(
    "FIRECRAWL_ONLY_MAIN_CONTENT",
    True,
)

FIRECRAWL_BLOCK_ADS = _env_bool(
    "FIRECRAWL_BLOCK_ADS",
    True,
)


# ============================================================
# EMBEDDINGS
# ============================================================

EMBEDDING_MODEL = _env_string(
    "EMBEDDING_MODEL",
    "BAAI/bge-small-en-v1.5",
)

EMBEDDING_NORMALIZE = _env_bool(
    "EMBEDDING_NORMALIZE",
    True,
)

EMBEDDING_BATCH_SIZE = _env_int(
    "EMBEDDING_BATCH_SIZE",
    32,
)

EMBEDDING_DEVICE = _env_string(
    "EMBEDDING_DEVICE",
    "auto",
)


# ============================================================
# CHUNKING
# ============================================================

CHUNK_SIZE = _env_int(
    "CHUNK_SIZE",
    1000,
)

CHUNK_OVERLAP = _env_int(
    "CHUNK_OVERLAP",
    200,
)

MIN_CHUNK_CHARS = _env_int(
    "MIN_CHUNK_CHARS",
    100,
)

MAX_CHUNK_CHARS = _env_int(
    "MAX_CHUNK_CHARS",
    2000,
)


# ============================================================
# CHROMADB
# ============================================================

CHROMA_PATH = _env_string(
    "CHROMA_PATH",
    str(PROJECT_ROOT / "chroma_db"),
)

CHROMA_COLLECTION = _env_string(
    "CHROMA_COLLECTION",
    "website_rag",
)

CHROMA_COLLECTION_NAME = CHROMA_COLLECTION


# ============================================================
# RETRIEVAL
# ============================================================

TOP_K = _env_int(
    "TOP_K",
    8,
)

RETRIEVAL_CANDIDATES = _env_int(
    "RETRIEVAL_CANDIDATES",
    30,
)

MIN_SEMANTIC_SCORE = _env_float(
    "MIN_SEMANTIC_SCORE",
    0.25,
)

MIN_HYBRID_SCORE = _env_float(
    "MIN_HYBRID_SCORE",
    0.20,
)

SEMANTIC_WEIGHT = _env_float(
    "SEMANTIC_WEIGHT",
    0.82,
)

LEXICAL_WEIGHT = _env_float(
    "LEXICAL_WEIGHT",
    0.18,
)


# ============================================================
# WHOLE-PAGE RETRIEVAL
# ============================================================

# IMPORTANT:
# These variables fix the ImportError from retriever.py.
# ============================================================

WHOLE_PAGE_PULL_ENABLED = _env_bool(
    "WHOLE_PAGE_PULL_ENABLED",
    True,
)

WHOLE_PAGE_PULL_SCORE_MARGIN = _env_float(
    "WHOLE_PAGE_PULL_SCORE_MARGIN",
    0.08,
)

WHOLE_PAGE_PULL_MAX_CHUNKS = _env_int(
    "WHOLE_PAGE_PULL_MAX_CHUNKS",
    20,
)


# ============================================================
# RAG CONTEXT
# ============================================================

MAX_CONTEXT_CHARS = _env_int(
    "MAX_CONTEXT_CHARS",
    28000,
)

MAX_SOURCES = _env_int(
    "MAX_SOURCES",
    10,
)

RETRIEVAL_PREVIEW_CHARS = _env_int(
    "RETRIEVAL_PREVIEW_CHARS",
    500,
)


# ============================================================
# URL / DOCUMENT SETTINGS
# ============================================================

REQUEST_USER_AGENT = _env_string(
    "REQUEST_USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36 "
        "WebRAG-Studio"
    ),
)


# ============================================================
# STREAMLIT
# ============================================================

STREAMLIT_PAGE_TITLE = _env_string(
    "STREAMLIT_PAGE_TITLE",
    "WebRAG Studio",
)


# ============================================================
# VALIDATION
# ============================================================

def validate_config() -> None:

    if CRAWL_LIMIT < 1:
        raise ValueError(
            "CRAWL_LIMIT must be >= 1."
        )

    if CRAWL_MAX_DEPTH < 1:
        raise ValueError(
            "CRAWL_MAX_DEPTH must be >= 1."
        )

    if CRAWL_DISCOVERY_LIMIT < CRAWL_LIMIT:
        print(
            "[CONFIG WARNING] "
            "CRAWL_DISCOVERY_LIMIT < CRAWL_LIMIT. "
            "Increasing it."
        )

        globals()["CRAWL_DISCOVERY_LIMIT"] = (
            CRAWL_LIMIT * 10
        )

    allowed_scope_modes = {
        "path",
        "domain",
        "same-domain",
        "same_domain",
        "same_path",
    }

    if SCOPE_MODE not in allowed_scope_modes:
        print(
            f"[CONFIG WARNING] "
            f"Invalid SCOPE_MODE={SCOPE_MODE!r}. "
            f"Using 'path'."
        )

        globals()["SCOPE_MODE"] = "path"

    if CHUNK_SIZE <= 0:
        raise ValueError(
            "CHUNK_SIZE must be greater than 0."
        )

    if CHUNK_OVERLAP < 0:
        raise ValueError(
            "CHUNK_OVERLAP cannot be negative."
        )

    if CHUNK_OVERLAP >= CHUNK_SIZE:
        raise ValueError(
            "CHUNK_OVERLAP must be smaller than CHUNK_SIZE."
        )

    if TOP_K < 1:
        raise ValueError(
            "TOP_K must be >= 1."
        )

    if RETRIEVAL_CANDIDATES < TOP_K:
        print(
            "[CONFIG WARNING] "
            "RETRIEVAL_CANDIDATES < TOP_K. "
            "Increasing it."
        )

        globals()["RETRIEVAL_CANDIDATES"] = TOP_K

    if SEMANTIC_WEIGHT < 0:
        raise ValueError(
            "SEMANTIC_WEIGHT cannot be negative."
        )

    if LEXICAL_WEIGHT < 0:
        raise ValueError(
            "LEXICAL_WEIGHT cannot be negative."
        )

    if (
        SEMANTIC_WEIGHT + LEXICAL_WEIGHT
    ) <= 0:
        raise ValueError(
            "SEMANTIC_WEIGHT + LEXICAL_WEIGHT "
            "must be greater than 0."
        )

    if MAX_CONTEXT_CHARS < 1000:
        raise ValueError(
            "MAX_CONTEXT_CHARS is too small."
        )

    if not OLLAMA_HOST:
        raise ValueError(
            "OLLAMA_HOST cannot be empty."
        )

    if not OLLAMA_MODEL:
        raise ValueError(
            "OLLAMA_MODEL cannot be empty."
        )

    if not EMBEDDING_MODEL:
        raise ValueError(
            "EMBEDDING_MODEL cannot be empty."
        )


validate_config()


# ============================================================
# CONFIGURATION DISPLAY
# ============================================================

print()
print("=" * 75)
print("WEBRAG STUDIO CONFIGURATION")
print("=" * 75)

print(f"CRAWL_LIMIT                  = {CRAWL_LIMIT}")
print(f"CRAWL_MAX_DEPTH              = {CRAWL_MAX_DEPTH}")
print(f"CRAWL_DISCOVERY_LIMIT        = {CRAWL_DISCOVERY_LIMIT}")
print(f"MAX_LINKS_PER_PAGE           = {MAX_LINKS_PER_PAGE}")
print(f"SCOPE_MODE                   = {SCOPE_MODE}")

print(
    f"USE_SITEMAP_SEED             = "
    f"{USE_SITEMAP_SEED}"
)

print(
    f"USE_FIRECRAWL_FALLBACK      = "
    f"{USE_FIRECRAWL_FALLBACK}"
)

print(
    f"WHOLE_PAGE_PULL_ENABLED      = "
    f"{WHOLE_PAGE_PULL_ENABLED}"
)

print(
    f"WHOLE_PAGE_PULL_SCORE_MARGIN = "
    f"{WHOLE_PAGE_PULL_SCORE_MARGIN}"
)

print(
    f"WHOLE_PAGE_PULL_MAX_CHUNKS   = "
    f"{WHOLE_PAGE_PULL_MAX_CHUNKS}"
)

print(f"OLLAMA_MODEL                 = {OLLAMA_MODEL}")
print(f"EMBEDDING_MODEL              = {EMBEDDING_MODEL}")
print(f"CHUNK_SIZE                   = {CHUNK_SIZE}")
print(f"CHUNK_OVERLAP                = {CHUNK_OVERLAP}")
print(f"TOP_K                        = {TOP_K}")
print(f"RETRIEVAL_CANDIDATES         = {RETRIEVAL_CANDIDATES}")
print(f"CHROMA_COLLECTION            = {CHROMA_COLLECTION}")

print("=" * 75)
