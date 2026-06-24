import gzip
from io import BytesIO
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import httpx

from audit.models import AuditFinding, Evidence
from audit.utils import get_origin


COMMON_SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemap1.xml",
]


async def fetch_text_url(url: str) -> tuple[int | None, str | None, str | None]:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 AgenticReportBot/0.1"
                },
            )

        content = response.content

        if url.endswith(".gz"):
            try:
                content = gzip.GzipFile(fileobj=BytesIO(content)).read()
            except Exception:
                pass

        text = content.decode("utf-8", errors="replace")
        return response.status_code, text, None

    except Exception as e:
        return None, None, str(e)


def parse_sitemap_xml(xml_text: str) -> tuple[list[str], list[str]]:
    """
    Returns:
    - page URLs from <url><loc>
    - child sitemap URLs from <sitemap><loc>
    """
    page_urls: list[str] = []
    child_sitemaps: list[str] = []

    try:
        root = ET.fromstring(xml_text)

        for element in root.iter():
            tag = element.tag.split("}")[-1].lower()

            if tag == "url":
                loc = None
                for child in element:
                    if child.tag.split("}")[-1].lower() == "loc":
                        loc = child.text
                        break

                if loc:
                    page_urls.append(loc.strip())

            elif tag == "sitemap":
                loc = None
                for child in element:
                    if child.tag.split("}")[-1].lower() == "loc":
                        loc = child.text
                        break

                if loc:
                    child_sitemaps.append(loc.strip())

    except ET.ParseError:
        return [], []

    return sorted(set(page_urls)), sorted(set(child_sitemaps))


async def discover_sitemaps(url: str, robots_sitemaps: list[str]) -> list[str]:
    origin = get_origin(url)

    candidates = set(robots_sitemaps)

    for path in COMMON_SITEMAP_PATHS:
        candidates.add(urljoin(origin, path))

    working_sitemaps = []

    for sitemap_url in candidates:
        status, text, _error = await fetch_text_url(sitemap_url)

        if status == 200 and text and "<" in text:
            page_urls, child_sitemaps = parse_sitemap_xml(text)

            if page_urls or child_sitemaps:
                working_sitemaps.append(sitemap_url)

    return sorted(set(working_sitemaps))


async def collect_sitemap_urls(
    url: str,
    robots_sitemaps: list[str],
    max_urls: int = 200,
) -> tuple[list[AuditFinding], list[str]]:
    findings: list[AuditFinding] = []
    discovered_sitemaps = await discover_sitemaps(url, robots_sitemaps)

    all_page_urls: list[str] = []
    child_sitemaps_seen: set[str] = set()

    for sitemap_url in discovered_sitemaps[:10]:
        status, text, error = await fetch_text_url(sitemap_url)

        if status != 200 or not text:
            continue

        page_urls, child_sitemaps = parse_sitemap_xml(text)

        all_page_urls.extend(page_urls)

        for child in child_sitemaps:
            if child in child_sitemaps_seen:
                continue

            child_sitemaps_seen.add(child)

            child_status, child_text, _child_error = await fetch_text_url(child)

            if child_status == 200 and child_text:
                child_page_urls, _grandchildren = parse_sitemap_xml(child_text)
                all_page_urls.extend(child_page_urls)

            if len(all_page_urls) >= max_urls:
                break

        if len(all_page_urls) >= max_urls:
            break

    all_page_urls = sorted(set(all_page_urls))[:max_urls]

    if discovered_sitemaps:
        findings.append(
            AuditFinding(
                check_id="sitemap_found",
                category="Crawlability & Indexability",
                title="XML sitemap found",
                status="pass",
                severity="low",
                confidence="high",
                evidence=[
                    Evidence(
                        url=sitemap_url,
                        signal="Sitemap found",
                    )
                    for sitemap_url in discovered_sitemaps[:10]
                ],
                affected_urls_count=len(all_page_urls),
                recommendation="No action required if the sitemap contains only canonical, indexable, 200-status URLs.",
                business_impact="Sitemaps help search engines discover important pages efficiently.",
                priority_score=1.0,
            )
        )

        if all_page_urls:
            findings.append(
                AuditFinding(
                    check_id="sitemap_urls_collected",
                    category="Crawlability & Indexability",
                    title="Sitemap URLs collected",
                    status="pass",
                    severity="low",
                    confidence="high",
                    evidence=[
                        Evidence(
                            url=page_url,
                            signal="Sitemap URL",
                        )
                        for page_url in all_page_urls[:10]
                    ],
                    affected_urls_count=len(all_page_urls),
                    recommendation="Use these URLs as part of the audit sample and validate that key templates are represented.",
                    business_impact="Sitemap URLs provide a useful sample of important indexable pages.",
                    priority_score=1.0,
                )
            )
    else:
        findings.append(
            AuditFinding(
                check_id="sitemap_missing",
                category="Crawlability & Indexability",
                title="No XML sitemap found",
                status="warning",
                severity="medium",
                confidence="medium",
                evidence=[
                    Evidence(
                        url=urljoin(get_origin(url), "/sitemap.xml"),
                        signal="No valid sitemap found at common locations",
                    )
                ],
                affected_urls_count=0,
                recommendation="Create and submit an XML sitemap containing canonical, indexable URLs.",
                business_impact="Without a sitemap, discovery of deeper pages may be less efficient.",
                priority_score=4.5,
            )
        )

    return findings, all_page_urls