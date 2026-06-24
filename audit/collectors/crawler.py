from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from audit.collectors.schema import extract_schema_data, extract_schema_types
from audit.models import PageFetchResult, PageSignals


def is_internal_link(base_url: str, link_url: str) -> bool:
    base_host = urlparse(base_url).netloc.replace("www.", "")
    link_host = urlparse(link_url).netloc.replace("www.", "")
    return base_host == link_host


def extract_page_signals(fetch_result: PageFetchResult) -> PageSignals:
    """
    Extract SEO, link, schema, and tracking signals from a fetched HTML page.

    Important:
    - Only extracts page-level SEO signals from 200-status HTML pages.
    - Non-200 pages are returned with status/redirect/error data only.
    """

    if not fetch_result.html or fetch_result.status_code != 200:
        return PageSignals(
            url=fetch_result.url,
            final_url=fetch_result.final_url,
            status_code=fetch_result.status_code,
            redirect_chain=fetch_result.redirect_chain,
            error=fetch_result.error,
        )

    soup = BeautifulSoup(fetch_result.html, "lxml")

    body_text = soup.get_text(" ", strip=True)
    body_text_sample = body_text[:3000] if body_text else None

    # Title
    title = soup.title.get_text(strip=True) if soup.title else None

    if not title:
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            title = og_title.get("content").strip()

    # Meta description, with OpenGraph fallback
    meta_description_tag = soup.find("meta", attrs={"name": "description"})

    if not meta_description_tag:
        meta_description_tag = soup.find("meta", attrs={"property": "og:description"})

    meta_description = (
        meta_description_tag.get("content", "").strip()
        if meta_description_tag and meta_description_tag.get("content")
        else None
    )

    # H1s
    h1s = [
        h.get_text(" ", strip=True)
        for h in soup.find_all("h1")
        if h.get_text(" ", strip=True)
    ]

    # Canonicals
    canonical_tags = []

    for tag in soup.find_all("link"):
        rel = tag.get("rel")

        if not rel:
            continue

        if isinstance(rel, list):
            rel_values = [str(value).lower() for value in rel]
        else:
            rel_values = [str(rel).lower()]

        if "canonical" in rel_values:
            canonical_tags.append(tag)

    canonicals = [
        urljoin(fetch_result.final_url, tag.get("href"))
        for tag in canonical_tags
        if tag.get("href")
    ]

    # Meta robots
    meta_robots_tag = soup.find("meta", attrs={"name": "robots"})
    meta_robots = (
        meta_robots_tag.get("content", "").strip()
        if meta_robots_tag and meta_robots_tag.get("content")
        else None
    )

    # Links
    internal_links = []
    external_links = []

    for a in soup.find_all("a", href=True):
        href = a.get("href")

        if not href:
            continue

        absolute = urljoin(fetch_result.final_url, href)
        parsed = urlparse(absolute)

        if parsed.scheme not in ["http", "https"]:
            continue

        if is_internal_link(fetch_result.final_url, absolute):
            internal_links.append(absolute)
        else:
            external_links.append(absolute)

    # Schema / structured data
    schema_data = extract_schema_data(fetch_result.html, fetch_result.final_url)
    schema_types = extract_schema_types(fetch_result.html, fetch_result.final_url)

    # Tracking detection
    page_html_lower = fetch_result.html.lower()

    tracking_signals = []

    tracking_patterns = {
        "Google Tag Manager": [
            "googletagmanager.com/gtm.js",
            "gtm-",
        ],
        "Google Analytics / GA4": [
            "google-analytics.com",
            "gtag/js",
            "g-",
        ],
        "Google Ads": [
            "googleadservices.com",
            "aw-",
        ],
        "Meta Pixel": [
            "connect.facebook.net",
            "fbq(",
        ],
        "TikTok Pixel": [
            "analytics.tiktok.com",
            "ttq.",
        ],
        "Hotjar": [
            "static.hotjar.com",
            "hj(",
        ],
        "Microsoft Clarity": [
            "clarity.ms",
            "clarity(",
        ],
    }

    for label, patterns in tracking_patterns.items():
        if any(pattern in page_html_lower for pattern in patterns):
            tracking_signals.append(label)
            
        # Tracking detection
    page_html_lower = fetch_result.html.lower()

    tracking_signals = []

    tracking_patterns = {
        "Google Tag Manager": ["googletagmanager.com/gtm.js", "gtm-"],
        "Google Analytics / GA4": ["google-analytics.com", "gtag/js", "g-"],
        "Google Ads": ["googleadservices.com", "aw-"],
        "Meta Pixel": ["connect.facebook.net", "fbq("],
        "TikTok Pixel": ["analytics.tiktok.com", "ttq."],
        "Hotjar": ["static.hotjar.com", "hj("],
        "Microsoft Clarity": ["clarity.ms", "clarity("],
    }

    for label, patterns in tracking_patterns.items():
        if any(pattern in page_html_lower for pattern in patterns):
            tracking_signals.append(label)

    return PageSignals(
        url=fetch_result.url,
        final_url=fetch_result.final_url,
        status_code=fetch_result.status_code,
        title=title,
        meta_description=meta_description,
        schema_data=schema_data,
        body_text_sample=body_text_sample,
        h1s=sorted(set(h1s)),
        canonicals=sorted(set(canonicals)),
        meta_robots=meta_robots,
        internal_links=sorted(set(internal_links)),
        external_links=sorted(set(external_links)),
        schema_types=sorted(set(schema_types)),
        tracking_signals=sorted(set(tracking_signals)),
        redirect_chain=fetch_result.redirect_chain,
        error=fetch_result.error,
    )