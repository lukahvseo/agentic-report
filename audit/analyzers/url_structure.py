from urllib.parse import urlparse, parse_qs
from audit.models import AuditFinding, Evidence, PageSignals


def analyze_url_structure(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    html_pages = [p for p in pages if p.status_code == 200]

    parameter_urls = []
    uppercase_urls = []
    long_urls = []
    deep_urls = []

    for page in html_pages:
        parsed = urlparse(page.final_url)
        path = parsed.path or "/"

        if parsed.query:
            parameter_urls.append(page)

        if any(char.isupper() for char in path):
            uppercase_urls.append(page)

        if len(page.final_url) > 115:
            long_urls.append(page)

        depth = len([part for part in path.split("/") if part])
        if depth >= 5:
            deep_urls.append(page)

    if parameter_urls:
        findings.append(
            AuditFinding(
                check_id="parameter_urls_detected",
                category="URL Structure",
                title="Parameter URLs detected",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(parameter_urls),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="URL contains query parameters",
                        details=", ".join(parse_qs(urlparse(p.final_url).query).keys()),
                    )
                    for p in parameter_urls[:10]
                ],
                recommendation="Review parameter URLs for duplicate content, crawl waste, canonicalization, and faceted navigation issues.",
                business_impact="Parameter-heavy URLs can create duplicate content and inefficient crawling.",
                priority_score=5.5,
            )
        )

    if uppercase_urls:
        findings.append(
            AuditFinding(
                check_id="uppercase_urls_detected",
                category="URL Structure",
                title="Uppercase characters detected in URLs",
                status="warning",
                severity="low",
                confidence="high",
                affected_urls_count=len(uppercase_urls),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Uppercase URL path",
                    )
                    for p in uppercase_urls[:10]
                ],
                recommendation="Use lowercase URLs consistently and redirect uppercase variants to lowercase canonical URLs.",
                business_impact="Inconsistent casing can create duplicate URL variants on some servers.",
                priority_score=3.0,
            )
        )

    if long_urls:
        findings.append(
            AuditFinding(
                check_id="long_urls_detected",
                category="URL Structure",
                title="Long URLs detected",
                status="warning",
                severity="low",
                confidence="medium",
                affected_urls_count=len(long_urls),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal=f"URL length: {len(p.final_url)} characters",
                    )
                    for p in long_urls[:10]
                ],
                recommendation="Review long URLs and simplify where possible, especially for category, product, and landing page templates.",
                business_impact="Long URLs are harder to read, share, and manage. They may also indicate overly complex site structure.",
                priority_score=2.5,
            )
        )

    if deep_urls:
        findings.append(
            AuditFinding(
                check_id="deep_urls_detected",
                category="URL Structure",
                title="Deep URL paths detected",
                status="warning",
                severity="medium",
                confidence="medium",
                affected_urls_count=len(deep_urls),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Deep URL path",
                        details=f"Path depth: {len([part for part in urlparse(p.final_url).path.split('/') if part])}",
                    )
                    for p in deep_urls[:10]
                ],
                recommendation="Review deeply nested URLs and confirm that important pages are reachable within a shallow, logical structure.",
                business_impact="Deep URLs may reflect poor architecture or important pages being buried too far from the homepage.",
                priority_score=4.0,
            )
        )

    if not findings:
        findings.append(
            AuditFinding(
                check_id="url_structure_clean",
                category="URL Structure",
                title="No major URL structure issues detected",
                status="pass",
                severity="low",
                confidence="medium",
                affected_urls_count=0,
                evidence=[],
                recommendation="No major URL structure issues detected in the sampled URLs.",
                business_impact="Sampled URLs appear reasonably clean and crawl-friendly.",
                priority_score=1.0,
            )
        )

    return findings