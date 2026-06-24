from audit.models import AuditFinding, Evidence, PageSignals


IMPORTANT_SCHEMA_TYPES = {
    "Organization",
    "WebSite",
    "WebPage",
    "BreadcrumbList",
    "Product",
    "Offer",
    "AggregateRating",
    "Review",
    "FAQPage",
    "Article",
    "BlogPosting",
    "LocalBusiness",
}


def analyze_schema(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    html_pages = [p for p in pages if p.status_code == 200]

    pages_without_schema = [
        p for p in html_pages
        if not p.schema_types
    ]

    pages_with_schema = [
        p for p in html_pages
        if p.schema_types
    ]

    all_schema_types = sorted(
        set(
            schema_type
            for page in pages_with_schema
            for schema_type in page.schema_types
        )
    )

    product_like_urls = [
        p for p in html_pages
        if any(
            marker in p.final_url.lower()
            for marker in ["/product/", "/products/", "/shop/", "/p/"]
        )
    ]

    product_pages_without_product_schema = [
        p for p in product_like_urls
        if "Product" not in p.schema_types
    ]

    if pages_without_schema and len(pages_without_schema) == len(html_pages):
        findings.append(
            AuditFinding(
                check_id="schema_missing_sitewide",
                category="Structured Data",
                title="No structured data detected on sampled pages",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(pages_without_schema),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="No schema detected",
                    )
                    for p in pages_without_schema[:10]
                ],
                recommendation="Add structured data for key templates, starting with Organization, WebSite, BreadcrumbList, and Product schema where relevant.",
                business_impact="Structured data helps search engines understand the site and can support rich result eligibility.",
                priority_score=5.5,
            )
        )

    elif pages_without_schema:
        findings.append(
            AuditFinding(
                check_id="schema_missing_on_some_pages",
                category="Structured Data",
                title="Some sampled pages are missing structured data",
                status="warning",
                severity="low",
                confidence="medium",
                affected_urls_count=len(pages_without_schema),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="No schema detected",
                    )
                    for p in pages_without_schema[:10]
                ],
                recommendation="Review templates without structured data and add relevant schema where it supports search understanding or rich results.",
                business_impact="Missing schema may reduce search engines’ ability to understand page entities and relationships.",
                priority_score=3.5,
            )
        )

    if product_pages_without_product_schema:
        findings.append(
            AuditFinding(
                check_id="product_schema_missing",
                category="Structured Data",
                title="Product-like URLs without Product schema detected",
                status="warning",
                severity="high",
                confidence="medium",
                affected_urls_count=len(product_pages_without_product_schema),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Product-like URL without Product schema",
                        details=f"Detected schema: {', '.join(p.schema_types) or 'none'}",
                    )
                    for p in product_pages_without_product_schema[:10]
                ],
                recommendation="Add Product schema with Offer fields such as price, availability, currency, and product identifiers where applicable.",
                business_impact="Product schema can improve product understanding and rich result eligibility.",
                priority_score=7.0,
            )
        )

    if pages_with_schema:
        findings.append(
            AuditFinding(
                check_id="schema_detected",
                category="Structured Data",
                title="Structured data detected",
                status="pass",
                severity="low",
                confidence="high",
                affected_urls_count=len(pages_with_schema),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Schema detected",
                        details=", ".join(p.schema_types),
                    )
                    for p in pages_with_schema[:10]
                ],
                recommendation="Validate structured data for errors and ensure schema content matches visible page content.",
                business_impact=f"Detected schema types include: {', '.join(all_schema_types[:15])}",
                priority_score=1.0,
            )
        )

    if not html_pages:
        findings.append(
            AuditFinding(
                check_id="schema_unknown_no_html_pages",
                category="Structured Data",
                title="Schema could not be evaluated",
                status="unknown",
                severity="low",
                confidence="low",
                affected_urls_count=0,
                evidence=[],
                recommendation="Run the schema check on valid 200-status HTML pages.",
                business_impact="Structured data cannot be assessed without accessible HTML pages.",
                priority_score=1.0,
            )
        )

    return findings