from __future__ import annotations

import time
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

from app.config import (
    CRAWL_LIMIT,
    CRAWL_MAX_DEPTH,
    CRAWL_DISCOVERY_LIMIT,
    CRAWL_RETRY_ATTEMPTS,
    CRAWL_REQUEST_DELAY,
    LOCAL_REQUEST_TIMEOUT,
    MAX_LINKS_PER_PAGE,
    SCOPE_MODE,
    REQUEST_USER_AGENT,
    USE_FIRECRAWL_FALLBACK,
    FIRECRAWL_API_KEY,
    FIRECRAWL_FORMAT,
    FIRECRAWL_ONLY_MAIN_CONTENT,
    FIRECRAWL_BLOCK_ADS,
    BLOCKED_PATH_KEYWORDS,
    BLOCKED_EXTENSIONS,
)

from app.models import Document
from app.cleaner import clean_text


# ============================================================
# SCOPE MODES
# ============================================================

_DOMAIN_MODES = {
    "domain",
    "same-domain",
    "same_domain",
}

_PATH_MODES = {
    "path",
    "same_path",
}


# ============================================================
# JS / THIN CONTENT
# ============================================================

_THIN_CONTENT_THRESHOLD = 250


# ============================================================
# SCRAPER
# ============================================================

class WebScraper:

    def __init__(self) -> None:

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": REQUEST_USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )


    # ========================================================
    # URL NORMALIZATION
    # ========================================================

    @staticmethod
    def normalize_url(url: str) -> str:

        if not url:
            return ""

        url = url.strip()

        # Remove #fragment.
        url, _ = urldefrag(url)

        parsed = urlparse(url)

        if parsed.scheme.lower() not in {
            "http",
            "https",
        }:
            return ""

        if not parsed.netloc:
            return ""

        scheme = parsed.scheme.lower()

        domain = parsed.netloc.lower()

        # Remove default ports.
        if scheme == "https" and domain.endswith(":443"):
            domain = domain[:-4]

        if scheme == "http" and domain.endswith(":80"):
            domain = domain[:-3]

        path = parsed.path or "/"

        # Normalize duplicate trailing slash.
        if path != "/":
            path = path.rstrip("/")

        normalized = (
            f"{scheme}://"
            f"{domain}"
            f"{path}"
        )

        # Keep query parameters because some documentation
        # sites use them for legitimate pages.
        #
        # Tracking parameters are removed below.
        if parsed.query:

            query_parts = []

            for item in parsed.query.split("&"):

                if not item:
                    continue

                key = item.split("=", 1)[0].lower()

                if key in {
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_term",
                    "utm_content",
                    "gclid",
                    "fbclid",
                }:
                    continue

                query_parts.append(item)

            if query_parts:
                normalized += "?" + "&".join(
                    query_parts
                )

        return normalized


    # ========================================================
    # BUILD SCOPE
    # ========================================================

    @classmethod
    def build_scope(
        cls,
        start_url: str,
    ) -> dict:

        start_url = cls.normalize_url(
            start_url
        )

        parsed = urlparse(start_url)

        scheme = parsed.scheme.lower()

        domain = parsed.netloc.lower()

        mode = (
            SCOPE_MODE or "path"
        ).lower()


        # ----------------------------------------------------
        # DOMAIN MODE
        # ----------------------------------------------------

        if mode in _DOMAIN_MODES:

            return {
                "mode": "domain",
                "scheme": scheme,
                "domain": domain,
                "path": "/",
            }


        # ----------------------------------------------------
        # PATH MODE
        #
        # IMPORTANT:
        #
        # We deliberately use the FIRST path segment.
        #
        # Example:
        #
        # /docs/home/
        #
        # becomes:
        #
        # /docs/
        #
        # NOT:
        #
        # /docs/home/
        # ----------------------------------------------------

        path_parts = [
            part.strip()
            for part in parsed.path.split("/")
            if part.strip()
        ]

        if not path_parts:

            scope_path = "/"

        else:

            first_segment = path_parts[0]

            scope_path = (
                f"/{first_segment}/"
            )


        return {
            "mode": "path",
            "scheme": scheme,
            "domain": domain,
            "path": scope_path,
        }


    # ========================================================
    # SCOPE PREFIX
    # ========================================================

    @classmethod
    def get_scope_prefix(
        cls,
        start_url: str,
    ) -> str:

        scope = cls.build_scope(
            start_url
        )

        if scope["mode"] == "domain":

            return (
                f"{scope['scheme']}://"
                f"{scope['domain']}/*"
            )

        return (
            f"{scope['scheme']}://"
            f"{scope['domain']}"
            f"{scope['path']}*"
        )


    # ========================================================
    # IN SCOPE?
    # ========================================================

    @classmethod
    def is_in_scope(
        cls,
        url: str,
        scope: dict,
    ) -> bool:

        normalized = cls.normalize_url(
            url
        )

        if not normalized:
            return False

        parsed = urlparse(
            normalized
        )

        # ----------------------------------------------------
        # Exact domain.
        # ----------------------------------------------------

        if (
            parsed.netloc.lower()
            != scope["domain"]
        ):
            return False

        # ----------------------------------------------------
        # Same protocol.
        # ----------------------------------------------------

        if (
            parsed.scheme.lower()
            != scope["scheme"]
        ):
            return False

        # ----------------------------------------------------
        # Whole domain.
        # ----------------------------------------------------

        if scope["mode"] == "domain":
            return True

        # ----------------------------------------------------
        # Path scope.
        # ----------------------------------------------------

        path = parsed.path or "/"

        scope_path = scope["path"]

        if scope_path == "/":
            return True

        return path.startswith(
            scope_path
        )


    # ========================================================
    # VALID DOCUMENTATION LINK?
    # ========================================================

    @staticmethod
    def is_valid_link(
        url: str,
    ) -> bool:

        if not url:
            return False

        parsed = urlparse(url)

        if parsed.scheme.lower() not in {
            "http",
            "https",
        }:
            return False

        path = (
            parsed.path or "/"
        ).lower()

        # ----------------------------------------------------
        # Block files.
        # ----------------------------------------------------

        for extension in BLOCKED_EXTENSIONS:

            if path.endswith(extension):
                return False


        # ----------------------------------------------------
        # Block unwanted paths.
        # ----------------------------------------------------

        for keyword in BLOCKED_PATH_KEYWORDS:

            if keyword in path:
                return False


        # ----------------------------------------------------
        # Additional non-document resources.
        # ----------------------------------------------------

        if path.startswith(
            "/cdn-cgi/"
        ):
            return False

        return True


    # ========================================================
    # FIRECRAWL CONTENT FALLBACK
    # ========================================================

    def _fetch_via_firecrawl(
        self,
        url: str,
    ) -> str | None:

        if (
            not USE_FIRECRAWL_FALLBACK
            or not FIRECRAWL_API_KEY
        ):
            return None

        try:

            response = requests.post(
                "https://api.firecrawl.dev/v1/scrape",

                headers={
                    "Authorization": (
                        f"Bearer "
                        f"{FIRECRAWL_API_KEY}"
                    ),
                    "Content-Type": (
                        "application/json"
                    ),
                },

                json={
                    "url": url,

                    "formats": [
                        FIRECRAWL_FORMAT
                    ],

                    "onlyMainContent":
                        FIRECRAWL_ONLY_MAIN_CONTENT,

                    "blockAds":
                        FIRECRAWL_BLOCK_ADS,
                },

                timeout=60,
            )

            response.raise_for_status()

            data = response.json()

            result = (
                data.get("data")
                or {}
            )

            text = result.get(
                FIRECRAWL_FORMAT
            )

            return text or None

        except Exception as exc:

            print(
                "[FIRECRAWL] "
                f"Failed for {url}: {exc}"
            )

            return None


    # ========================================================
    # HTTP GET WITH RETRIES
    # ========================================================

    def _get_with_retry(
        self,
        url: str,
    ):

        last_exception = None

        attempts = max(
            1,
            CRAWL_RETRY_ATTEMPTS + 1,
        )

        for attempt in range(
            attempts
        ):

            try:

                response = self.session.get(
                    url,
                    timeout=LOCAL_REQUEST_TIMEOUT,
                    allow_redirects=True,
                )

                response.raise_for_status()

                return response

            except requests.RequestException as exc:

                last_exception = exc

                if (
                    attempt
                    < attempts - 1
                ):

                    wait_time = (
                        0.5
                        * (attempt + 1)
                    )

                    print(
                        f"[RETRY] "
                        f"{attempt + 1}/"
                        f"{attempts - 1}"
                    )

                    time.sleep(
                        wait_time
                    )


        if last_exception:
            raise last_exception

        raise requests.RequestException(
            "Unknown request failure."
        )


    # ========================================================
    # EXTRACT PAGE
    # ========================================================

    def extract_page(
        self,
        url: str,
        scope: dict,
    ):

        try:

            print()
            print(
                f"[GET] {url}"
            )

            response = (
                self._get_with_retry(url)
            )

            final_url = (
                self.normalize_url(
                    response.url
                )
            )

            # ------------------------------------------------
            # Redirect must remain in scope.
            # ------------------------------------------------

            if not self.is_in_scope(
                final_url,
                scope,
            ):

                print(
                    "[SKIP] "
                    "Redirect escaped scope."
                )

                return None, []


            # ------------------------------------------------
            # Only HTML.
            # ------------------------------------------------

            content_type = (
                response.headers
                .get(
                    "Content-Type",
                    "",
                )
                .lower()
            )

            if (
                "text/html"
                not in content_type
            ):

                print(
                    "[SKIP] "
                    "Not HTML."
                )

                return None, []


            # ------------------------------------------------
            # Parse HTML.
            # ------------------------------------------------

            soup = BeautifulSoup(
                response.text,
                "lxml",
            )


            # ------------------------------------------------
            # Page title.
            # ------------------------------------------------

            title = ""

            if soup.title:

                title = (
                    soup.title
                    .get_text(
                        " ",
                        strip=True,
                    )
                )


            # =================================================
            # LINK DISCOVERY
            #
            # VERY IMPORTANT:
            #
            # We collect links BEFORE removing nav/sidebar.
            #
            # This means documentation sidebars count.
            # =================================================

            discovered_links = []

            for anchor in soup.find_all(
                "a",
                href=True,
            ):

                href = anchor.get(
                    "href"
                )

                if not href:
                    continue

                absolute_url = (
                    urljoin(
                        final_url,
                        href,
                    )
                )

                absolute_url = (
                    self.normalize_url(
                        absolute_url
                    )
                )

                if not absolute_url:
                    continue

                if not self.is_valid_link(
                    absolute_url
                ):
                    continue

                if not self.is_in_scope(
                    absolute_url,
                    scope,
                ):
                    continue

                discovered_links.append(
                    absolute_url
                )

                if (
                    len(discovered_links)
                    >= MAX_LINKS_PER_PAGE
                ):
                    break


            # ------------------------------------------------
            # Remove duplicates while keeping order.
            # ------------------------------------------------

            discovered_links = list(
                dict.fromkeys(
                    discovered_links
                )
            )


            # =================================================
            # EXTRACT CONTENT
            # =================================================

            for tag in soup(
                [
                    "script",
                    "style",
                    "noscript",
                    "svg",
                    "canvas",
                    "iframe",
                    "form",
                    "footer",
                ]
            ):

                tag.decompose()


            # ------------------------------------------------
            # Prefer main documentation content.
            # ------------------------------------------------

            main = (
                soup.find("main")
                or soup.find("article")
                or soup.find(
                    attrs={
                        "role": "main"
                    }
                )
                or soup.body
            )


            if main is not None:

                text = clean_text(
                    main.get_text(
                        "\n",
                        strip=True,
                    )
                )

            else:

                text = ""


            # =================================================
            # FIRECRAWL FALLBACK
            # =================================================

            if (
                len(text)
                < _THIN_CONTENT_THRESHOLD
            ):

                firecrawl_text = (
                    self._fetch_via_firecrawl(
                        final_url
                    )
                )

                if (
                    firecrawl_text
                    and len(firecrawl_text)
                    >= _THIN_CONTENT_THRESHOLD
                ):

                    text = clean_text(
                        firecrawl_text
                    )

                    crawl_method = (
                        "firecrawl"
                    )

                else:

                    crawl_method = (
                        "requests+bs4"
                    )

            else:

                crawl_method = (
                    "requests+bs4"
                )


            # =================================================
            # CONTENT TOO SMALL
            #
            # IMPORTANT:
            #
            # Even when content is too small,
            # we return discovered links.
            #
            # This allows the BFS to continue.
            # =================================================

            if len(text) < 100:

                print(
                    f"[NO CONTENT] "
                    f"{len(text)} chars"
                )

                print(
                    f"[LINKS FOUND] "
                    f"{len(discovered_links)}"
                )

                return (
                    None,
                    discovered_links,
                )


            # =================================================
            # DOCUMENT
            # =================================================

            document = Document(

                content=text,

                metadata={

                    "url": final_url,

                    "title": title,

                    "crawl_method":
                        crawl_method,

                    "discovered_links":
                        len(discovered_links),
                },
            )


            print(
                f"[CONTENT] "
                f"{len(text)} chars"
            )

            print(
                f"[LINKS] "
                f"{len(discovered_links)} "
                f"in-scope links"
            )


            return (
                document,
                discovered_links,
            )


        except requests.RequestException as exc:

            print(
                f"[REQUEST ERROR] "
                f"{url}: {exc}"
            )

            return None, []


        except Exception as exc:

            print(
                f"[EXTRACTION ERROR] "
                f"{url}: {exc}"
            )

            return None, []


    # ========================================================
    # BFS CRAWLER
    # ========================================================

    def crawl(
        self,
        start_url: str,
    ) -> list[Document]:

        # ----------------------------------------------------
        # Normalize starting URL.
        # ----------------------------------------------------

        start_url = (
            self.normalize_url(
                start_url
            )
        )

        if not start_url:

            raise ValueError(
                "Invalid starting URL."
            )


        # ----------------------------------------------------
        # Build scope.
        # ----------------------------------------------------

        scope = self.build_scope(
            start_url
        )


        # ====================================================
        # START INFORMATION
        # ====================================================

        print()
        print("=" * 80)
        print("WEBRAG LINK-GRAPH CRAWLER")
        print("=" * 80)

        print(
            f"Starting URL       : "
            f"{start_url}"
        )

        print(
            f"Scope mode         : "
            f"{scope['mode']}"
        )

        print(
            f"Allowed domain     : "
            f"{scope['domain']}"
        )

        print(
            f"Allowed path       : "
            f"{scope['path']}"
        )

        print(
            f"Maximum pages      : "
            f"{CRAWL_LIMIT}"
        )

        print(
            f"Maximum depth      : "
            f"{CRAWL_MAX_DEPTH}"
        )

        print(
            f"Discovery limit    : "
            f"{CRAWL_DISCOVERY_LIMIT}"
        )

        print(
            f"Links/page         : "
            f"{MAX_LINKS_PER_PAGE}"
        )

        print()
        print("CRAWL STRATEGY")
        print("-" * 80)

        print(
            "1. Start ONLY from the supplied URL."
        )

        print(
            "2. Crawl that page."
        )

        print(
            "3. Extract its <a href> links."
        )

        print(
            "4. Keep only in-scope links."
        )

        print(
            "5. Put those links into BFS queue."
        )

        print(
            "6. Crawl the next link."
        )

        print(
            "7. Repeat recursively."
        )

        print(
            "8. Stop at 500 usable pages."
        )

        print()
        print(
            "SITEMAP SEEDING: DISABLED"
        )

        print(
            "DOMAIN JUMPING: DISABLED"
        )

        print("=" * 80)


        # ====================================================
        # BFS DATA STRUCTURES
        # ====================================================

        queue = deque()

        queued = set()

        visited = set()

        documents = []

        discovery_count = 0


        # ====================================================
        # CRITICAL:
        #
        # THE ONLY INITIAL SEED.
        # ====================================================

        queue.append(
            (
                start_url,
                0,
            )
        )

        queued.add(
            start_url
        )


        print()
        print(
            f"[SEED] {start_url}"
        )


        # ====================================================
        # BFS LOOP
        # ====================================================

        while queue:

            # ------------------------------------------------
            # Maximum pages.
            # ------------------------------------------------

            if (
                len(documents)
                >= CRAWL_LIMIT
            ):

                print()
                print(
                    f"[STOP] "
                    f"Reached "
                    f"{CRAWL_LIMIT} pages."
                )

                break


            # ------------------------------------------------
            # Discovery safety.
            # ------------------------------------------------

            if (
                discovery_count
                >= CRAWL_DISCOVERY_LIMIT
            ):

                print()
                print(
                    "[STOP] "
                    "Discovery safety limit reached."
                )

                break


            # ------------------------------------------------
            # Get next URL.
            # ------------------------------------------------

            current_url, depth = (
                queue.popleft()
            )

            queued.discard(
                current_url
            )


            # ------------------------------------------------
            # Already visited?
            # ------------------------------------------------

            if current_url in visited:
                continue


            visited.add(
                current_url
            )

            discovery_count += 1


            # ------------------------------------------------
            # Scope check.
            # ------------------------------------------------

            if not self.is_in_scope(
                current_url,
                scope,
            ):

                print(
                    f"[OUT OF SCOPE] "
                    f"{current_url}"
                )

                continue


            # =================================================
            # CRAWL PAGE
            # =================================================

            print()
            print("-" * 80)

            print(
                f"PAGE "
                f"{len(documents) + 1}/"
                f"{CRAWL_LIMIT}"
            )

            print(
                f"DEPTH: {depth}"
            )

            print(
                f"VISITED: "
                f"{discovery_count}"
            )

            print(
                f"QUEUE: "
                f"{len(queue)}"
            )

            print(
                f"URL: "
                f"{current_url}"
            )

            print("-" * 80)


            document, links = (
                self.extract_page(
                    current_url,
                    scope,
                )
            )


            # =================================================
            # STORE PAGE
            # =================================================

            if document is not None:

                document.metadata[
                    "depth"
                ] = depth

                documents.append(
                    document
                )

                print(
                    f"[SAVED] "
                    f"Page "
                    f"{len(documents)}"
                )

            else:

                print(
                    "[NOT STORED]"
                )


            # =================================================
            # FOLLOW DISCOVERED LINKS
            # =================================================

            if depth < CRAWL_MAX_DEPTH:

                new_links = 0

                for link in links:

                    # ----------------------------------------
                    # Already visited?
                    # ----------------------------------------

                    if link in visited:
                        continue

                    # ----------------------------------------
                    # Already queued?
                    # ----------------------------------------

                    if link in queued:
                        continue

                    # ----------------------------------------
                    # Must be in scope.
                    # ----------------------------------------

                    if not self.is_in_scope(
                        link,
                        scope,
                    ):
                        continue

                    # ----------------------------------------
                    # Add to BFS queue.
                    # ----------------------------------------

                    queue.append(
                        (
                            link,
                            depth + 1,
                        )
                    )

                    queued.add(
                        link
                    )

                    new_links += 1


                    # ----------------------------------------
                    # Safety.
                    # ----------------------------------------

                    if (
                        discovery_count
                        + len(queue)
                        >= CRAWL_DISCOVERY_LIMIT
                    ):

                        break


                print(
                    f"[NEW LINKS] "
                    f"{new_links}"
                )

            else:

                print(
                    "[DEPTH LIMIT] "
                    "Not following links from "
                    "this page."
                )


            # =================================================
            # DELAY
            # =================================================

            if (
                CRAWL_REQUEST_DELAY
                > 0
            ):

                time.sleep(
                    CRAWL_REQUEST_DELAY
                )


        # ====================================================
        # FINISHED
        # ====================================================

        print()
        print("=" * 80)
        print("CRAWLING FINISHED")
        print("=" * 80)

        print(
            f"Pages successfully extracted : "
            f"{len(documents)}"
        )

        print(
            f"Target maximum               : "
            f"{CRAWL_LIMIT}"
        )

        print(
            f"URLs visited                 : "
            f"{discovery_count}"
        )

        print(
            f"URLs remaining in queue      : "
            f"{len(queue)}"
        )

        print(
            f"Scope                         : "
            f"{self.get_scope_prefix(start_url)}"
        )

        print("=" * 80)


        # ====================================================
        # IMPORTANT DIAGNOSTIC
        # ====================================================

        if (
            len(documents)
            < CRAWL_LIMIT
        ):

            print()
            print("=" * 80)
            print("WHY DID THE CRAWL STOP?")
            print("=" * 80)

            if not queue:

                print(
                    "The BFS queue is empty."
                )

                print(
                    "That means the crawler could not "
                    "discover more usable in-scope "
                    "<a href> pages from the pages "
                    "it actually visited."
                )

            elif (
                discovery_count
                >= CRAWL_DISCOVERY_LIMIT
            ):

                print(
                    "The discovery safety limit "
                    "was reached."
                )

            elif (
                CRAWL_MAX_DEPTH > 0
            ):

                print(
                    "The maximum crawl depth "
                    "was reached."
                )

            print()
            print(
                "This is NOT because sitemap.xml "
                "was ignored."
            )

            print(
                "This crawler intentionally uses "
                "ONLY the link graph starting "
                "from your supplied URL."
            )

            print("=" * 80)


        # ====================================================
        # PRINT URL LIST
        # ====================================================

        print()
        print("CRAWLED PAGES")
        print("-" * 80)

        for index, document in enumerate(
            documents,
            start=1,
        ):

            print(
                f"{index:03d}. "
                f"{document.metadata.get('url')}"
            )


        return documents