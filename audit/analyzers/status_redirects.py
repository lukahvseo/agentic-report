from urllib.parse import urlparse

from audit.models import AuditFinding, Evidence, PageSignals


def strip_trailing_slash(url: str) -> str:
    parsed = urlparse(url)

    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return parsed._replace(path=path).geturl()


def normalize_for_comparison(url: str) -> str:
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().replace("www.", "")

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return parsed._replace(
        scheme=scheme,
        netloc=netloc,
        path=path,
        fragment="",
    ).geturl()


def canonical_matches_final_url(page: PageSignals) -> bool:
    if not page.canonicals:
        return False

    final_normalized = normalize_for_comparison(page.final_url)

    return any(
        normalize_for_comparison(canonical) == final_normalized
        for canonical in page.canonicals
    )


def is_likely_normalization_redirect(page: PageSignals) -> bool:
    if not page.redirect_chain:
        return False

    if len(page.redirect_chain) > 1:
        return False

    if page.status_code != 200:
        return False

    requested = page.url
    final = page.final_url

    requested_parsed = urlparse(requested)
    final_parsed = urlparse(final)

    same_host = (
        requested_parsed.netloc.lower().replace("www.", "")
        == final_parsed.netloc.lower().replace("www.", "")
    )

    if not same_host:
        return False

    requested_norm = normalize_for_comparison(requested)
    final_norm = normalize_for_comparison(final)

    # Handles trailing slash, www/non-www, scheme normalization, and casing after normalization.
    if requested_norm == final_norm:
        return True

    # If canonical points to the final URL, this is very likely intentional.
    if canonical_matches_final_url(page):
        return True

    return False


def analyze_status_and_redirects(pages: list[PageSignals]) -> list[AuditFinding]:
    findings = []

    error_pages = [
        p for p in pages
        if p.status_code is None or p.status_code >= 400
    ]

    redirect_pages = [
        p for p in pages
        if len(p.redirect_chain) > 0
    ]

    acceptable_redirects = [
        p for p in redirect_pages
        if is_likely_normalization_redirect(p)
    ]

    problematic_redirects = [
        p for p in redirect_pages
        if not is_likely_normalization_redirect(p)
    ]

    long_redirect_chains = [
        p for p in pages
        if len(p.redirect_chain) > 1
    ]

    if error_pages:
        has_many_403s = sum(1 for p in error_pages if p.status_code == 403) >= max(
            3,
            len(error_pages) // 2,
        )

        recommendation = (
            "The sampled URLs are returning 403 Forbidden. Confirm whether the site is intentionally blocking crawlers, "
            "SEO tools, or non-browser requests. If these pages load normally in a browser, classify this as an audit-access "
            "limitation rather than a true broken-page issue. If Googlebot or Merchant Center is also blocked, this is critical."
            if has_many_403s
            else "Fix or redirect URLs returning 4xx or 5xx status codes, especially if they are internally linked or used as Merchant Center landing pages."
        )

        business_impact = (
            "If legitimate crawlers such as Googlebot or Merchant Center are blocked, the site can suffer indexing, crawling, and Shopping approval issues."
            if has_many_403s
            else "Broken URLs can hurt crawlability, user experience, and Shopping landing page eligibility."
        )

        findings.append(
            AuditFinding(
                check_id="http_error_pages",
                category="Technical SEO",
                title="HTTP error pages detected",
                status="fail",
                severity="critical" if has_many_403s else "high",
                confidence="high",
                affected_urls_count=len(error_pages),
                evidence=[
                    Evidence(
                        url=p.url,
                        signal=f"HTTP status {p.status_code}",
                        details=p.error,
                    )
                    for p in error_pages[:10]
                ],
                recommendation=recommendation,
                business_impact=business_impact,
                priority_score=9.5 if has_many_403s else 8.5,
            )
        )

    if long_redirect_chains:
        findings.append(
            AuditFinding(
                check_id="redirect_chains",
                category="Technical SEO",
                title="Redirect chains detected",
                status="fail",
                severity="high",
                confidence="high",
                affected_urls_count=len(long_redirect_chains),
                evidence=[
                    Evidence(
                        url=p.url,
                        signal="Redirect chain",
                        details=" → ".join(p.redirect_chain + [p.final_url]),
                    )
                    for p in long_redirect_chains[:10]
                ],
                recommendation="Reduce redirect chains so each URL redirects directly to its final destination in one hop.",
                business_impact="Redirect chains slow down users and crawlers and can weaken signal consolidation.",
                priority_score=7.5,
            )
        )

    if problematic_redirects:
        findings.append(
            AuditFinding(
                check_id="problematic_redirects_detected",
                category="Technical SEO",
                title="Potentially problematic redirects detected",
                status="warning",
                severity="medium",
                confidence="medium",
                affected_urls_count=len(problematic_redirects),
                evidence=[
                    Evidence(
                        url=p.url,
                        signal="Redirect may need review",
                        details=(
                            " → ".join(p.redirect_chain + [p.final_url])
                            + (
                                f" | Canonical: {', '.join(p.canonicals)}"
                                if p.canonicals
                                else " | Canonical: missing"
                            )
                        ),
                    )
                    for p in problematic_redirects[:10]
                ],
                recommendation="Review redirected URLs where the final URL does not appear to be a simple normalization target or where the canonical does not clearly match the final URL.",
                business_impact="Unexpected redirects can create crawl inefficiency, tracking inconsistencies, and landing page mismatch risks.",
                priority_score=5.5,
            )
        )

    if acceptable_redirects:
        findings.append(
            AuditFinding(
                check_id="normalization_redirects_detected",
                category="Technical SEO",
                title="Acceptable URL normalization redirects detected",
                status="pass",
                severity="low",
                confidence="high",
                affected_urls_count=len(acceptable_redirects),
                evidence=[
                    Evidence(
                        url=p.url,
                        signal="Acceptable normalization redirect",
                        details=(
                            " → ".join(p.redirect_chain + [p.final_url])
                            + (
                                f" | Canonical: {', '.join(p.canonicals)}"
                                if p.canonicals
                                else ""
                            )
                        ),
                    )
                    for p in acceptable_redirects[:10]
                ],
                recommendation="No action required. These redirects appear to normalize URLs to the canonical version.",
                business_impact="URL normalization helps consolidate signals and prevent duplicate URL variants.",
                priority_score=1.0,
            )
        )

    if not findings:
        findings.append(
            AuditFinding(
                check_id="status_redirects_clean",
                category="Technical SEO",
                title="No major status or redirect issues detected",
                status="pass",
                severity="low",
                confidence="high",
                evidence=[],
                affected_urls_count=0,
                recommendation="No action required for the sampled URLs.",
                business_impact="The sampled URLs are technically accessible and do not show problematic redirect behavior.",
                priority_score=1.0,
            )
        )

    return findings