from urllib.parse import urljoin
import httpx

from audit.models import AuditFinding, Evidence
from audit.utils import get_origin


async def fetch_robots_txt(url: str) -> tuple[str, int | None, str | None]:
    origin = get_origin(url)
    robots_url = urljoin(origin, "/robots.txt")

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(
                robots_url,
                headers={
                    "User-Agent": "Mozilla/5.0 AgenticReportBot/0.1"
                },
            )

        text = response.text if response.status_code == 200 else None
        return robots_url, response.status_code, text

    except Exception as e:
        return robots_url, None, str(e)


def extract_sitemap_urls_from_robots(robots_text: str | None) -> list[str]:
    if not robots_text:
        return []

    sitemap_urls = []

    for line in robots_text.splitlines():
        clean = line.strip()

        if clean.lower().startswith("sitemap:"):
            sitemap_url = clean.split(":", 1)[1].strip()
            if sitemap_url:
                sitemap_urls.append(sitemap_url)

    return sorted(set(sitemap_urls))


async def analyze_robots_txt(url: str) -> tuple[list[AuditFinding], list[str]]:
    robots_url, status_code, robots_text = await fetch_robots_txt(url)
    sitemap_urls = extract_sitemap_urls_from_robots(robots_text)

    findings: list[AuditFinding] = []

    if status_code == 200:
        findings.append(
            AuditFinding(
                check_id="robots_txt_found",
                category="Crawlability & Indexability",
                title="robots.txt is accessible",
                status="pass",
                severity="low",
                confidence="high",
                evidence=[
                    Evidence(
                        url=robots_url,
                        signal="robots.txt found",
                        details=f"Status code: {status_code}",
                    )
                ],
                affected_urls_count=0,
                recommendation="No action required. Continue ensuring robots.txt does not block important URLs.",
                business_impact="An accessible robots.txt gives crawlers clear crawl instructions.",
                priority_score=1.0,
            )
        )
    elif status_code == 404:
        findings.append(
            AuditFinding(
                check_id="robots_txt_missing",
                category="Crawlability & Indexability",
                title="robots.txt is missing",
                status="warning",
                severity="low",
                confidence="high",
                evidence=[
                    Evidence(
                        url=robots_url,
                        signal="robots.txt missing",
                        details="Status code: 404",
                    )
                ],
                affected_urls_count=0,
                recommendation="Add a simple robots.txt file and reference the XML sitemap.",
                business_impact="A missing robots.txt is not always harmful, but it removes a useful crawl-control and sitemap-discovery signal.",
                priority_score=3.0,
            )
        )
    else:
        findings.append(
            AuditFinding(
                check_id="robots_txt_unavailable",
                category="Crawlability & Indexability",
                title="robots.txt could not be reliably checked",
                status="warning",
                severity="medium",
                confidence="medium",
                evidence=[
                    Evidence(
                        url=robots_url,
                        signal="robots.txt unavailable",
                        details=f"Status code or error: {status_code}",
                    )
                ],
                affected_urls_count=0,
                recommendation="Check that robots.txt is accessible and not returning server errors.",
                business_impact="If robots.txt is unavailable due to server errors, crawler behavior may be unpredictable.",
                priority_score=4.0,
            )
        )

    if sitemap_urls:
        findings.append(
            AuditFinding(
                check_id="robots_sitemap_reference_found",
                category="Crawlability & Indexability",
                title="Sitemap reference found in robots.txt",
                status="pass",
                severity="low",
                confidence="high",
                evidence=[
                    Evidence(
                        url=sitemap_url,
                        signal="Sitemap reference",
                    )
                    for sitemap_url in sitemap_urls[:10]
                ],
                affected_urls_count=len(sitemap_urls),
                recommendation="No action required unless the referenced sitemap URLs are invalid.",
                business_impact="Sitemap references help crawlers discover important URLs.",
                priority_score=1.0,
            )
        )
    else:
        findings.append(
            AuditFinding(
                check_id="robots_sitemap_reference_missing",
                category="Crawlability & Indexability",
                title="No sitemap reference found in robots.txt",
                status="warning",
                severity="low",
                confidence="high" if robots_text else "medium",
                evidence=[
                    Evidence(
                        url=robots_url,
                        signal="No Sitemap directive found",
                    )
                ],
                affected_urls_count=0,
                recommendation="Add a Sitemap directive to robots.txt, for example: Sitemap: https://example.com/sitemap.xml",
                business_impact="This can make sitemap discovery less reliable for search engines and audit tools.",
                priority_score=2.5,
            )
        )

    return findings, sitemap_urls