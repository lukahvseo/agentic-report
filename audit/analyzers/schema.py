from audit.models import AuditFinding, Evidence, PageSignals


def page_has_schema_type(page: PageSignals, schema_type: str) -> bool:
    normalized_target = schema_type.lower()

    for item in page.schema_types:
        normalized_item = str(item).lower()

        if normalized_item == normalized_target:
            return True

        if normalized_item.endswith(f"/{normalized_target}"):
            return True

    return False


def build_missing_schema_finding(
    page: PageSignals,
    required_schema: str,
    page_type_label: str,
    status: str,
    severity: str,
    priority_score: float,
    recommendation: str,
    business_impact: str,
) -> AuditFinding:
    return AuditFinding(
        check_id=f"{page.page_type}_{required_schema.lower()}_schema_missing",
        category="Structured Data",
        title=f"Missing {required_schema} schema on {page_type_label} page",
        status=status,
        severity=severity,
        confidence="high",
        affected_urls_count=1,
        evidence=[
            Evidence(
                url=page.final_url,
                signal="Schema types detected",
                details=(
                    ", ".join(page.schema_types)
                    if page.schema_types
                    else "No schema types detected"
                ),
            )
        ],
        recommendation=recommendation,
        business_impact=business_impact,
        priority_score=priority_score,
    )


def analyze_collection_page_schema(page: PageSignals) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    if not page_has_schema_type(page, "CollectionPage"):
        findings.append(
            build_missing_schema_finding(
                page=page,
                required_schema="CollectionPage",
                page_type_label="collection",
                status="fail",
                severity="high",
                priority_score=8.0,
                recommendation="Add CollectionPage schema to collection/category pages so search engines can better understand the page as a product listing or category page.",
                business_impact="Missing CollectionPage schema can weaken structured understanding of ecommerce category pages and reduce eligibility for enhanced search interpretation.",
            )
        )

    if not page_has_schema_type(page, "FAQPage"):
        findings.append(
            build_missing_schema_finding(
                page=page,
                required_schema="FAQPage",
                page_type_label="collection",
                status="warning",
                severity="medium",
                priority_score=5.0,
                recommendation="Add FAQPage schema when the collection page includes visible FAQ content that answers common buying, sizing, shipping, or category questions.",
                business_impact="FAQ schema can reinforce topical relevance and help connect important collection pages with common pre-purchase questions.",
            )
        )

    if not page_has_schema_type(page, "BreadcrumbList"):
        findings.append(
            build_missing_schema_finding(
                page=page,
                required_schema="BreadcrumbList",
                page_type_label="collection",
                status="warning",
                severity="low",
                priority_score=3.0,
                recommendation="Add BreadcrumbList schema to collection/category pages to clarify site hierarchy and category structure.",
                business_impact="Breadcrumb schema can help search engines understand navigation paths and how the collection fits within the wider ecommerce catalog.",
            )
        )

    return findings


def analyze_product_page_schema(page: PageSignals) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    if not page_has_schema_type(page, "Product"):
        findings.append(
            build_missing_schema_finding(
                page=page,
                required_schema="Product",
                page_type_label="product",
                status="fail",
                severity="high",
                priority_score=8.5,
                recommendation="Add Product schema to product pages with name, image, description, offers, price, currency, availability, brand, SKU/GTIN/MPN, and review data when available.",
                business_impact="Missing Product schema can reduce eligibility for product-rich results and weaken search engines' ability to understand commercial product information.",
            )
        )

    if not page_has_schema_type(page, "FAQPage"):
        findings.append(
            build_missing_schema_finding(
                page=page,
                required_schema="FAQPage",
                page_type_label="product",
                status="warning",
                severity="medium",
                priority_score=5.0,
                recommendation="Add FAQPage schema when the product page includes visible FAQ content about sizing, shipping, returns, materials, usage, warranty, or care instructions.",
                business_impact="FAQ schema can support buyer confidence and help search engines connect product pages with common pre-purchase questions.",
            )
        )

    if not page_has_schema_type(page, "BreadcrumbList"):
        findings.append(
            build_missing_schema_finding(
                page=page,
                required_schema="BreadcrumbList",
                page_type_label="product",
                status="warning",
                severity="low",
                priority_score=3.0,
                recommendation="Add BreadcrumbList schema to product pages to clarify the product's category path and site hierarchy.",
                business_impact="Breadcrumb schema can improve structured understanding of where the product sits within the ecommerce catalog.",
            )
        )

    return findings


def analyze_generic_schema_presence(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    pages_without_schema = [
        page for page in pages
        if page.status_code == 200 and not page.schema_types
    ]

    if pages_without_schema:
        findings.append(
            AuditFinding(
                check_id="schema_missing_generic",
                category="Structured Data",
                title="Some pages have no structured data detected",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(pages_without_schema),
                evidence=[
                    Evidence(
                        url=page.final_url,
                        signal="No schema detected",
                        details=f"Page type: {page.page_type}",
                    )
                    for page in pages_without_schema[:10]
                ],
                recommendation="Add relevant structured data based on page type, such as Organization, WebSite, BreadcrumbList, Product, CollectionPage, Article, or FAQPage schema.",
                business_impact="Pages without structured data may be harder for search engines and AI systems to interpret accurately.",
                priority_score=4.0,
            )
        )

    return findings


def analyze_schema(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    for page in pages:
        if page.status_code != 200:
            continue

        if page.page_type == "collection":
            findings.extend(analyze_collection_page_schema(page))

        elif page.page_type == "product":
            findings.extend(analyze_product_page_schema(page))

    findings.extend(analyze_generic_schema_presence(pages))

    return findings