from audit.models import AuditResult
from audit.collectors.robots import analyze_robots_txt
from audit.collectors.sitemap import collect_sitemap_urls
from audit.collectors.site_crawler import crawl_site_sample
from audit.analyzers.status_redirects import analyze_status_and_redirects
from audit.analyzers.indexability import analyze_indexability
from audit.analyzers.onpage import analyze_onpage
from audit.analyzers.schema import analyze_schema
from audit.analyzers.url_structure import analyze_url_structure
from audit.analyzers.trust_pages import analyze_trust_pages
from audit.analyzers.tracking import analyze_tracking
from audit.analyzers.page_type import apply_page_types
from audit.analyzers.ecommerce_canonical import analyze_ecommerce_canonicals
from audit.analyzers.ecommerce_schema import analyze_product_schema_completeness

async def run_audit(
    url: str,
    max_pages: int = 50,
    manual_urls: list[str] | None = None,
    crawl_mode: str = "auto",
) -> AuditResult:
    """
    crawl_mode:
    - auto: homepage + sitemap + discovered internal links
    - manual: homepage + manual URLs only
    - hybrid: homepage + manual URLs + sitemap + discovered internal links
    """

    findings = []
    manual_urls = manual_urls or []

    robots_findings, robots_sitemaps = await analyze_robots_txt(url)
    findings.extend(robots_findings)

    sitemap_urls = []

    if crawl_mode in ["auto", "hybrid"]:
        sitemap_findings, sitemap_urls = await collect_sitemap_urls(
            url=url,
            robots_sitemaps=robots_sitemaps,
            max_urls=max_pages,
        )
        findings.extend(sitemap_findings)

    if crawl_mode == "manual":
        seed_urls = manual_urls
        discover_links = False
    elif crawl_mode == "hybrid":
        seed_urls = list(set(manual_urls + sitemap_urls[:max_pages]))
        discover_links = True
    else:
        seed_urls = sitemap_urls[:max_pages]
        discover_links = True

    pages = await crawl_site_sample(
        start_url=url,
        seed_urls=seed_urls,
        max_pages=max_pages,
        concurrency=5,
        discover_links=discover_links,
    )

    pages = apply_page_types(pages)

    findings.extend(analyze_status_and_redirects(pages))
    findings.extend(analyze_indexability(pages))
    findings.extend(analyze_onpage(pages))
    findings.extend(analyze_schema(pages))
    findings.extend(analyze_url_structure(pages))
    findings.extend(analyze_trust_pages(pages))
    findings.extend(analyze_tracking(pages))
    findings.extend(analyze_ecommerce_canonicals(pages))
    findings.extend(analyze_product_schema_completeness(pages))

    final_url = pages[0].final_url if pages else None

    findings = sorted(
        findings,
        key=lambda finding: finding.priority_score,
        reverse=True,
    )

    return AuditResult(
        input_url=url,
        final_url=final_url,
        pages_checked=len(pages),
        findings=findings,
        page_signals=pages,
    )