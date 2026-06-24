from audit.models import AuditFinding, Evidence, PageSignals


def analyze_indexability(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    noindex_pages = []
    missing_canonical_pages = []
    multiple_canonical_pages = []

    for page in pages:
        robots = (page.meta_robots or "").lower()

        if "noindex" in robots:
            noindex_pages.append(page)

        if page.status_code == 200:
            if not page.canonicals:
                missing_canonical_pages.append(page)
            elif len(page.canonicals) > 1:
                multiple_canonical_pages.append(page)

    if noindex_pages:
        findings.append(
            AuditFinding(
                check_id="noindex_pages_detected",
                category="Crawlability & Indexability",
                title="Noindex pages detected",
                status="warning",
                severity="high",
                confidence="high",
                affected_urls_count=len(noindex_pages),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="meta robots noindex",
                        details=p.meta_robots,
                    )
                    for p in noindex_pages[:10]
                ],
                recommendation="Review noindex pages and confirm that important SEO or Merchant Center landing pages are not blocked from indexing.",
                business_impact="Important pages with noindex cannot appear in organic search results.",
                priority_score=8.0,
            )
        )

    if missing_canonical_pages:
        findings.append(
            AuditFinding(
                check_id="missing_canonical_tags",
                category="Crawlability & Indexability",
                title="Canonical tags missing on indexable pages",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(missing_canonical_pages),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Missing canonical",
                    )
                    for p in missing_canonical_pages[:10]
                ],
                recommendation="Add self-referencing canonical tags to canonical indexable pages.",
                business_impact="Canonical tags help consolidate duplicate URL signals and reduce indexing ambiguity.",
                priority_score=5.0,
            )
        )

    if multiple_canonical_pages:
        findings.append(
            AuditFinding(
                check_id="multiple_canonical_tags",
                category="Crawlability & Indexability",
                title="Multiple canonical tags detected",
                status="fail",
                severity="high",
                confidence="high",
                affected_urls_count=len(multiple_canonical_pages),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Multiple canonical tags",
                        details=", ".join(p.canonicals),
                    )
                    for p in multiple_canonical_pages[:10]
                ],
                recommendation="Ensure each page has only one canonical tag.",
                business_impact="Multiple canonicals can send conflicting indexing signals to search engines.",
                priority_score=7.5,
            )
        )

    if not findings:
        findings.append(
            AuditFinding(
                check_id="basic_indexability_clean",
                category="Crawlability & Indexability",
                title="No major noindex or canonical issues detected",
                status="pass",
                severity="low",
                confidence="medium",
                evidence=[],
                affected_urls_count=0,
                recommendation="No major indexability action required for the sampled URLs.",
                business_impact="Sampled pages appear broadly indexable based on meta robots and canonical signals.",
                priority_score=1.0,
            )
        )

    return findings