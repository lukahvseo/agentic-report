import asyncio
from collections import deque

from audit.collectors.fetcher import fetch_url
from audit.collectors.crawler import extract_page_signals
from audit.models import PageSignals
from audit.utils import normalize_url, same_domain, looks_like_html_page
from audit.utils import normalize_url, same_domain, looks_like_html_page, ensure_url_scheme


async def crawl_site_sample(
    start_url: str,
    seed_urls: list[str] | None = None,
    max_pages: int = 50,
    concurrency: int = 5,
    discover_links: bool = True,
) -> list[PageSignals]:
    """
    Controlled crawler for URL-only audit.

    Modes:
    - discover_links=True: crawl start_url + seed URLs + discovered internal links
    - discover_links=False: only crawl start_url + seed URLs
    """

    queue = deque()
    seen: set[str] = set()
    results: list[PageSignals] = []

    def add_url(url: str):
        normalized = normalize_url(ensure_url_scheme(url))
        if normalized in seen:
            return

        if not same_domain(start_url, normalized):
            return

        if not looks_like_html_page(normalized):
            return

        seen.add(normalized)
        queue.append(normalized)

    add_url(start_url)

    for seed in seed_urls or []:
        add_url(seed)

    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_and_extract(url: str) -> PageSignals:
        async with semaphore:
            fetch_result = await fetch_url(url)
            return extract_page_signals(fetch_result)

    while queue and len(results) < max_pages:
        batch = []

        while queue and len(batch) < concurrency and len(results) + len(batch) < max_pages:
            batch.append(queue.popleft())

        page_results = await asyncio.gather(
            *[fetch_and_extract(url) for url in batch]
        )

        for page in page_results:
            results.append(page)

            if not discover_links:
                continue

            for link in page.internal_links:
                if len(seen) >= max_pages * 3:
                    break
                add_url(link)

    return results