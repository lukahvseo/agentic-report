from urllib.parse import urlparse, parse_qs, urlunparse

from audit.models import AuditFinding, Evidence, PageSignals


VARIANT_PARAMS = {
    "variant",
    "variant_id",
    "variation",
    "attribute_pa_size",
    "attribute_pa_color",
    "color",
    "size",
}


def remove_query_params(url: str, params_to_remove: set[str]) -> str:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    kept_params = {
        key: value
        for key, value in query_params.items()
        if key.lower() not in params_to_remove
    }

    query_string_parts = []

    for key, values in kept_params.items():
        for value in values:
            query_string_parts.append(f"{key}={value}")

    new_query = "&".join(query_string_parts)

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            new_query,
            "",
        )
    )


def normalize_url_for_canonical_compare(url: str) -> str:
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().replace("www.", "")

    path = parsed.path or "/"

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            parsed.query,
            "",
        )
    )


def has_variant_parameter(url: str) -> bool:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    return any(param.lower() in VARIANT_PARAMS for param in query_params.keys())


def expected_variant_canonical(url: str) -> str:
    return remove_query_params(url, VARIANT_PARAMS)


def canonical_matches_expected(page: PageSignals, expected: str) -> bool:
    expected_normalized = normalize_url_for_canonical_compare(expected)

    return any(
        normalize_url_for_canonical_compare(canonical) == expected_normalized
        for canonical in page.canonicals
    )


def analyze_ecommerce_canonicals(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    product_variant_pages = [
        page for page in pages
        if page.status_code == 200
        and page.page_type == "product"
        and has_variant_parameter(page.url)
    ]

    missing_canonical = []
    incorrect_variant_canonical = []
    correct_variant_canonical = []

    for page in product_variant_pages:
        expected = expected_variant_canonical(page.url)

        if not page.canonicals:
            missing_canonical.append((page, expected))
        elif canonical_matches_expected(page, expected):
            correct_variant_canonical.append((page, expected))
        else:
            incorrect_variant_canonical.append((page, expected))

    if missing_canonical:
        findings.append(
            AuditFinding(
                check_id="product_variant_canonical_missing",
                category="Ecommerce Canonicalization",
                title="Product variant URLs are missing canonical tags",
                status="fail",
                severity="high",
                confidence="high",
                affected_urls_count=len(missing_canonical),
                evidence=[
                    Evidence(
                        url=page.final_url,
                        signal="Missing canonical on variant URL",
                        details=f"Expected canonical: {expected}",
                    )
                    for page, expected in missing_canonical[:10]
                ],
                recommendation="Add canonical tags from product variant URLs to the clean parent product URL without variant parameters.",
                business_impact="Variant URLs without canonical tags can create duplicate product URLs and dilute ranking signals.",
                priority_score=8.0,
            )
        )

    if incorrect_variant_canonical:
        findings.append(
            AuditFinding(
                check_id="product_variant_canonical_incorrect",
                category="Ecommerce Canonicalization",
                title="Product variant URLs have incorrect canonical targets",
                status="fail",
                severity="high",
                confidence="high",
                affected_urls_count=len(incorrect_variant_canonical),
                evidence=[
                    Evidence(
                        url=page.url,
                        signal="Incorrect variant canonical",
                        details=(
                            f"Expected: {expected} | "
                            f"Found: {', '.join(page.canonicals)}"
                        ),
                    )
                    for page, expected in incorrect_variant_canonical[:10]
                ],
                recommendation="Canonicalize variant URLs to the clean parent product URL unless each variant has unique indexable content and a dedicated SEO strategy.",
                business_impact="Incorrect variant canonicals can cause duplicate content, indexing noise, and weaker product page consolidation.",
                priority_score=8.5,
            )
        )

    if correct_variant_canonical:
        findings.append(
            AuditFinding(
                check_id="product_variant_canonical_correct",
                category="Ecommerce Canonicalization",
                title="Product variant canonicals are configured correctly",
                status="pass",
                severity="low",
                confidence="high",
                affected_urls_count=len(correct_variant_canonical),
                evidence=[
                    Evidence(
                        url=page.url,
                        signal="Variant canonical points to clean product URL",
                        details=f"Canonical: {', '.join(page.canonicals)}",
                    )
                    for page, expected in correct_variant_canonical[:10]
                ],
                recommendation="No action required. Variant URLs appear to canonicalize to the clean parent product URL.",
                business_impact="Correct variant canonicalization helps consolidate product ranking signals.",
                priority_score=1.0,
            )
        )

    return findings