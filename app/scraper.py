from __future__ import annotations

import time
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
from xml.etree import ElementTree as ET

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
    USE_SITEMAP_SEED,
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
# CONTENT SETTINGS
# ============================================================

_THIN_CONTENT_THRESHOLD = 250

_MIN_DOCUMENT_CHARS = 100

_MAX_SITEMAPS = 10


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

                "Accept-Language": (
                    "en-US,en;q=0.9"
                ),
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

        # Remove fragment.
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

        # Normalize trailing slash.
        if path != "/":
            path = path.rstrip("/")

        normalized = (
            f"{scheme}://"
            f"{domain}"
            f"{path}"
        )

        # Keep legitimate query parameters.
        # Remove tracking parameters.
        if parsed.query:

            query_parts = []

            for item in parsed.query.split("&"):

                if not item:
                    continue

                key = item.split(
                    "=",
                    1,
                )[0].lower()

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

                normalized += (
                    "?"
                    + "&".join(
                        query_parts
                    )
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
        # Example:
        #
        # https://example.com/docs/home/
        #
        # becomes:
        #
        # https://example.com/docs/*
        #
        # This is intentionally broader than /docs/home/.
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

        # Exact domain.
        if (
            parsed.netloc.lower()
            != scope["domain"]
        ):
            return False

        # Same protocol.
        if (
            parsed.scheme.lower()
            != scope["scheme"]
        ):
            return False

        # Whole domain.
        if scope["mode"] == "domain":
            return True

        # Path mode.
        path = parsed.path or "/"

        scope_path = scope["path"]

        if scope_path == "/":
            return True

        return path.startswith(
            scope_path
        )


    # ========================================================
    # VALID LINK
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
        # Block file extensions.
        # ----------------------------------------------------

        for extension in BLOCKED_EXTENSIONS:

            if path.endswith(extension):

                return False


        # ----------------------------------------------------
        # Block unwanted paths.
        # ----------------------------------------------------

        for keyword in BLOCKED_PATH_KEYWORDS:

            if keyword.lower() in path:

                return False


        # ----------------------------------------------------
        # Cloudflare internal paths.
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

                response = (
                    self.session.get(

                        url,

                        timeout=(
                            LOCAL_REQUEST_TIMEOUT
                        ),

                        allow_redirects=True,
                    )
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
                        "[RETRY] "
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
    # SITEMAP DISCOVERY
    #
    # This is a FALLBACK.
    #
    # Normal crawling still starts from the URL and follows
    # normal HTML links first.
    # ========================================================

    def _discover_sitemap_urls(
        self,
        start_url: str,
        scope: dict,
    ) -> list[str]:

        if not USE_SITEMAP_SEED:

            return []


        parsed = urlparse(
            start_url
        )

        origin = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
        )


        # ----------------------------------------------------
        # First check robots.txt.
        # ----------------------------------------------------

        robots_url = (
            f"{origin}/robots.txt"
        )

        sitemap_candidates = []


        try:

            response = self.session.get(
                robots_url,
                timeout=LOCAL_REQUEST_TIMEOUT,
            )

            if response.ok:

                for line in response.text.splitlines():

                    line = line.strip()

                    if line.lower().startswith(
                        "sitemap:"
                    ):

                        sitemap_url = (
                            line.split(
                                ":",
                                1,
                            )[1].strip()
                        )

                        if sitemap_url:

                            sitemap_candidates.append(
                                sitemap_url
                            )


        except Exception as exc:

            print(
                "[SITEMAP] "
                f"robots.txt failed: {exc}"
            )


        # ----------------------------------------------------
        # Common sitemap locations.
        # ----------------------------------------------------

        sitemap_candidates.extend(
            [
                f"{origin}/sitemap.xml",
                f"{origin}/sitemap_index.xml",
                f"{origin}/sitemap-index.xml",
            ]
        )


        # Remove duplicates.
        sitemap_candidates = list(
            dict.fromkeys(
                sitemap_candidates
            )
        )


        sitemap_urls = []

        visited_sitemaps = set()

        sitemap_queue = deque(
            sitemap_candidates
        )


        while (
            sitemap_queue
            and len(visited_sitemaps)
            < _MAX_SITEMAPS
        ):

            sitemap_url = sitemap_queue.popleft()

            sitemap_url = (
                self.normalize_url(
                    sitemap_url
                )
            )

            if not sitemap_url:
                continue

            if sitemap_url in visited_sitemaps:
                continue

            visited_sitemaps.add(
                sitemap_url
            )


            print(
                f"[SITEMAP CHECK] "
                f"{sitemap_url}"
            )


            try:

                response = self.session.get(
                    sitemap_url,
                    timeout=LOCAL_REQUEST_TIMEOUT,
                )

                if not response.ok:

                    continue


                content = response.text

                root = ET.fromstring(
                    content
                )


                # Remove XML namespace.
                tag_name = (
                    root.tag
                    .split("}")
                    [-1]
                    .lower()
                )


                # ------------------------------------------------
                # Sitemap index.
                # ------------------------------------------------

                if tag_name == "sitemapindex":

                    for element in root:

                        child_tag = (
                            element.tag
                            .split("}")
                            [-1]
                            .lower()
                        )

                        if child_tag != "sitemap":
                            continue

                        for child in element:

                            child_name = (
                                child.tag
                                .split("}")
                                [-1]
                                .lower()
                            )

                            if child_name == "loc":

                                child_url = (
                                    child.text
                                    or ""
                                ).strip()

                                if child_url:

                                    sitemap_queue.append(
                                        child_url
                                    )


                # ------------------------------------------------
                # Normal URL sitemap.
                # ------------------------------------------------

                elif tag_name == "urlset":

                    for element in root:

                        child_tag = (
                            element.tag
                            .split("}")
                            [-1]
                            .lower()
                        )

                        if child_tag != "url":
                            continue

                        for child in element:

                            child_name = (
                                child.tag
                                .split("}")
                                [-1]
                                .lower()
                            )

                            if child_name != "loc":
                                continue

                            page_url = (
                                child.text
                                or ""
                            ).strip()

                            page_url = (
                                self.normalize_url(
                                    page_url
                                )
                            )

                            if not page_url:
                                continue

                            if not self.is_valid_link(
                                page_url
                            ):
                                continue

                            if not self.is_in_scope(
                                page_url,
                                scope,
                            ):
                                continue

                            sitemap_urls.append(
                                page_url
                            )


            except Exception as exc:

                print(
                    "[SITEMAP] "
                    f"Failed {sitemap_url}: "
                    f"{exc}"
                )


        sitemap_urls = list(
            dict.fromkeys(
                sitemap_urls
            )
        )


        print(
            f"[SITEMAP] "
            f"Discovered "
            f"{len(sitemap_urls)} "
            f"in-scope URLs."
        )


        return sitemap_urls


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
                self._get_with_retry(
                    url
                )
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
            # HTML only.
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
            # Title.
            # ------------------------------------------------

            title = ""

            if soup.title:

                title = (
                    soup.title.get_text(
                        " ",
                        strip=True,
                    )
                )


            # =================================================
            # LINK DISCOVERY
            #
            # IMPORTANT:
            #
            # Discover links BEFORE deleting navigation.
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


            # Remove duplicates.
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
            # Main content preference.
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
            # FIRECRAWL CONTENT FALLBACK
            # =================================================

            crawl_method = (
                "requests+bs4"
            )


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


            # =================================================
            # IMPORTANT
            #
            # Even if page content is poor,
            # discovered links are returned.
            # =================================================

            if len(text) < _MIN_DOCUMENT_CHARS:

                print(
                    "[NO CONTENT] "
                    f"{len(text)} chars"
                )

                print(
                    "[LINKS FOUND] "
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
                "[CONTENT] "
                f"{len(text)} chars"
            )

            print(
                "[LINKS] "
                f"{len(discovered_links)} "
                "in-scope links"
            )


            return (
                document,
                discovered_links,
            )


        except requests.RequestException as exc:

            print(
                "[REQUEST ERROR] "
                f"{url}: {exc}"
            )

            return None, []


        except Exception as exc:

            print(
                "[EXTRACTION ERROR] "
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
        # Normalize start URL.
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

        print(
            "WEBSITE DOCUMENTATION CRAWLER"
        )

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

        print(
            "CRAWL STRATEGY"
        )

        print("-" * 80)

        print(
            "1. Start from supplied URL."
        )

        print(
            "2. Discover normal HTML links."
        )

        print(
            "3. Crawl discovered links using BFS."
        )

        print(
            "4. If enabled, use sitemap as "
            "a discovery fallback."
        )

        print(
            "5. Respect domain/path scope."
        )

        print(
            "6. Stop at configured limits."
        )

        print("=" * 80)


        # ====================================================
        # BFS DATA
        # ====================================================

        queue = deque()

        queued = set()

        visited = set()

        documents = []

        discovery_count = 0


        # ====================================================
        # ONLY INITIAL SEED
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
        # HTML BFS
        # ====================================================

        while queue:

            # ------------------------------------------------
            # Page limit.
            # ------------------------------------------------

            if (
                len(documents)
                >= CRAWL_LIMIT
            ):

                print(
                    "[STOP] "
                    f"Reached {CRAWL_LIMIT} pages."
                )

                break


            # ------------------------------------------------
            # Discovery safety.
            # ------------------------------------------------

            if (
                discovery_count
                >= CRAWL_DISCOVERY_LIMIT
            ):

                print(
                    "[STOP] "
                    "Discovery safety limit reached."
                )

                break


            current_url, depth = (
                queue.popleft()
            )

            queued.discard(
                current_url
            )


            if current_url in visited:

                continue


            visited.add(
                current_url
            )

            discovery_count += 1


            if not self.is_in_scope(
                current_url,
                scope,
            ):

                print(
                    "[OUT OF SCOPE] "
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
                f"DEPTH   : {depth}"
            )

            print(
                f"VISITED : {discovery_count}"
            )

            print(
                f"QUEUE   : {len(queue)}"
            )

            print(
                f"URL     : {current_url}"
            )

            print("-" * 80)


            document, links = (
                self.extract_page(
                    current_url,
                    scope,
                )
            )


            # =================================================
            # STORE DOCUMENT
            # =================================================

            if document is not None:

                document.metadata[
                    "depth"
                ] = depth

                documents.append(
                    document
                )

                print(
                    "[SAVED] "
                    f"Page {len(documents)}"
                )

            else:

                print(
                    "[NOT STORED]"
                )


            # =================================================
            # FOLLOW HTML LINKS
            # =================================================

            if depth < CRAWL_MAX_DEPTH:

                new_links = 0


                for link in links:

                    if link in visited:
                        continue

                    if link in queued:
                        continue

                    if not self.is_in_scope(
                        link,
                        scope,
                    ):
                        continue


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


                    if (
                        discovery_count
                        + len(queue)
                        >= CRAWL_DISCOVERY_LIMIT
                    ):

                        break


                print(
                    "[NEW LINKS] "
                    f"{new_links}"
                )


            else:

                print(
                    "[DEPTH LIMIT]"
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
        # SITEMAP FALLBACK
        #
        # If normal HTML crawling did not discover enough
        # pages, use sitemap URLs as additional BFS seeds.
        # ====================================================

        if (
            USE_SITEMAP_SEED
            and len(documents)
            < CRAWL_LIMIT
        ):

            print()

            print("=" * 80)

            print(
                "HTML LINK GRAPH FINISHED"
            )

            print(
                f"Current pages: "
                f"{len(documents)}"
            )

            print(
                "Trying sitemap discovery..."
            )

            print("=" * 80)


            sitemap_urls = (
                self._discover_sitemap_urls(
                    start_url,
                    scope,
                )
            )


            sitemap_added = 0


            for sitemap_url in sitemap_urls:

                if (
                    len(documents)
                    >= CRAWL_LIMIT
                ):

                    break


                if (
                    sitemap_url in visited
                    or sitemap_url in queued
                ):

                    continue


                queue.append(
                    (
                        sitemap_url,
                        0,
                    )
                )

                queued.add(
                    sitemap_url
                )

                sitemap_added += 1


            print(
                "[SITEMAP] "
                f"Added {sitemap_added} "
                "URLs to crawl queue."
            )


            # =================================================
            # CRAWL SITEMAP URLS
            # =================================================

            while queue:

                if (
                    len(documents)
                    >= CRAWL_LIMIT
                ):

                    print(
                        "[STOP] "
                        f"Reached {CRAWL_LIMIT} pages."
                    )

                    break


                if (
                    discovery_count
                    >= CRAWL_DISCOVERY_LIMIT
                ):

                    print(
                        "[STOP] "
                        "Discovery safety limit reached."
                    )

                    break


                current_url, depth = (
                    queue.popleft()
                )

                queued.discard(
                    current_url
                )


                if current_url in visited:

                    continue


                visited.add(
                    current_url
                )

                discovery_count += 1


                if not self.is_in_scope(
                    current_url,
                    scope,
                ):

                    continue


                print()

                print("-" * 80)

                print(
                    f"SITEMAP PAGE "
                    f"{len(documents) + 1}/"
                    f"{CRAWL_LIMIT}"
                )

                print(
                    f"URL: {current_url}"
                )

                print("-" * 80)


                document, links = (
                    self.extract_page(
                        current_url,
                        scope,
                    )
                )


                if document is not None:

                    document.metadata[
                        "depth"
                    ] = depth

                    documents.append(
                        document
                    )

                    print(
                        "[SAVED] "
                        f"Page {len(documents)}"
                    )


                # Continue normal link discovery
                # from sitemap pages too.

                if depth < CRAWL_MAX_DEPTH:

                    for link in links:

                        if link in visited:
                            continue

                        if link in queued:
                            continue

                        if not self.is_in_scope(
                            link,
                            scope,
                        ):
                            continue


                        queue.append(
                            (
                                link,
                                depth + 1,
                            )
                        )

                        queued.add(
                            link
                        )


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

        print(
            "CRAWLING FINISHED"
        )

        print("=" * 80)

        print(
            "Pages successfully extracted : "
            f"{len(documents)}"
        )

        print(
            "Target maximum               : "
            f"{CRAWL_LIMIT}"
        )

        print(
            "URLs visited                 : "
            f"{discovery_count}"
        )

        print(
            "URLs remaining in queue      : "
            f"{len(queue)}"
        )

        print(
            "Scope                        : "
            f"{self.get_scope_prefix(start_url)}"
        )

        print("=" * 80)


        # ====================================================
        # DIAGNOSTIC
        # ====================================================

        if (
            len(documents)
            < CRAWL_LIMIT
        ):

            print()

            print("=" * 80)

            print(
                "CRAWL STOPPED BEFORE PAGE LIMIT"
            )

            print("=" * 80)


            if not queue:

                print(
                    "The crawl queue is empty."
                )

                print(
                    "The crawler could not discover "
                    "additional usable pages."
                )


            elif (
                discovery_count
                >= CRAWL_DISCOVERY_LIMIT
            ):

                print(
                    "Discovery safety limit reached."
                )


            elif (
                CRAWL_MAX_DEPTH > 0
            ):

                print(
                    "Maximum crawl depth reached."
                )


            print("=" * 80)


        # ====================================================
        # PRINT URL LIST
        # ====================================================

        print()

        print(
            "CRAWLED PAGES"
        )

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
