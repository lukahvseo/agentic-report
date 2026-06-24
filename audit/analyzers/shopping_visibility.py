from audit.models import AuditFinding, Evidence
from audit.collectors.shopping_serp import check_visibility_for_keywords


def build_shopping_findings_from_result(result: dict) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    rows = result.get("shopping_tab_rows", [])

    missing_rows = [
        row for row in rows
        if not row.get("found_on_shopping_tab")
    ]

    found_rows = [
        row for row in rows
        if row.get("found_on_shopping_tab")
    ]

    rows_without_reviews = [
        row for row in found_rows
        if not row.get("has_reviews")
    ]

    rows_without_price = [
        row for row in found_rows
        if not row.get("has_price")
    ]

    if missing_rows:
        findings.append(
            AuditFinding(
                check_id="shopping_visibility_missing",
                category="Search Results Visibility",
                title="Merchant not found in Google Shopping results for some keywords",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(missing_rows),
                evidence=[
                    Evidence(
                        signal="Not found in Shopping results",
                        details=(
                            f"Query: {row.get('query')} | "
                            f"Results checked: {row.get('results_checked')}"
                        ),
                    )
                    for row in missing_rows[:10]
                ],
                recommendation="Review Merchant Center eligibility, product feed quality, product titles, GTIN/MPN/brand fields, landing page quality, and Shopping competitiveness for these queries.",
                business_impact="If products do not appear for relevant Shopping queries, the merchant may be missing visibility for commercial search demand.",
                priority_score=6.5,
            )
        )

    if found_rows:
        findings.append(
            AuditFinding(
                check_id="shopping_visibility_found",
                category="Search Results Visibility",
                title="Merchant found in Google Shopping results",
                status="pass",
                severity="low",
                confidence="high",
                affected_urls_count=len(found_rows),
                evidence=[
                    Evidence(
                        url=row.get("matched_link") or None,
                        signal="Found in Shopping results",
                        details=(
                            f"Query: {row.get('query')} | "
                            f"Position: {row.get('position')} | "
                            f"Title: {row.get('matched_title')} | "
                            f"Match: {row.get('match_reason')}"
                        ),
                    )
                    for row in found_rows[:10]
                ],
                recommendation="No immediate visibility issue detected for these queries. Continue monitoring position, price display, ratings, and competitive coverage.",
                business_impact=f"Shopping visibility score: {result.get('shopping_tab_score')}%.",
                priority_score=1.0,
            )
        )

    if rows_without_price:
        findings.append(
            AuditFinding(
                check_id="shopping_price_missing",
                category="Search Results Visibility",
                title="Shopping results found without visible price data",
                status="warning",
                severity="medium",
                confidence="medium",
                affected_urls_count=len(rows_without_price),
                evidence=[
                    Evidence(
                        url=row.get("matched_link") or None,
                        signal="No price detected in Shopping result",
                        details=f"Query: {row.get('query')} | Title: {row.get('matched_title')}",
                    )
                    for row in rows_without_price[:10]
                ],
                recommendation="Check product feed price fields, landing page price consistency, structured data Offer price, and Merchant Center diagnostics.",
                business_impact="Missing or inconsistent price display can reduce Shopping visibility and user confidence.",
                priority_score=5.5,
            )
        )

    if rows_without_reviews:
        findings.append(
            AuditFinding(
                check_id="shopping_reviews_missing",
                category="Search Results Visibility",
                title="Shopping results found without visible review data",
                status="warning",
                severity="low",
                confidence="medium",
                affected_urls_count=len(rows_without_reviews),
                evidence=[
                    Evidence(
                        url=row.get("matched_link") or None,
                        signal="No review count detected in Shopping result",
                        details=f"Query: {row.get('query')} | Title: {row.get('matched_title')}",
                    )
                    for row in rows_without_reviews[:10]
                ],
                recommendation="Review product review collection, review feed eligibility, Product schema aggregateRating/review fields, and Merchant Center review integrations.",
                business_impact="Review visibility can improve trust and competitiveness in shopping-oriented SERPs.",
                priority_score=3.5,
            )
        )

    return findings


def analyze_shopping_visibility(
    domain: str,
    api_key: str,
    merchant_name: str,
    keywords: list[str],
    location: str = "",
    gl: str = "us",
    hl: str = "en",
    google_domain: str = "google.com",
) -> list[AuditFinding]:
    if not api_key or not keywords:
        return []

    result = check_visibility_for_keywords(
        domain=domain,
        api_key=api_key,
        merchant_name=merchant_name,
        keywords=keywords,
        location=location,
        gl=gl,
        hl=hl,
        google_domain=google_domain,
    )

    return build_shopping_findings_from_result(result)