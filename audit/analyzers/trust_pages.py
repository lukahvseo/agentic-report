from audit.models import AuditFinding, Evidence, PageSignals


TRUST_PATTERNS = {
    "contact": ["contact", "support", "help"],
    "privacy_policy": ["privacy"],
    "terms": ["terms", "terms-of-service", "terms-and-conditions"],
    "refund_returns": ["refund", "return", "returns"],
    "shipping": ["shipping", "delivery"],
    "about": ["about"],
}


def analyze_trust_pages(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    all_urls = sorted(
        set(
            [p.final_url for p in pages]
            + [
                link
                for page in pages
                for link in page.internal_links
            ]
        )
    )

    detected = {}
    missing = []

    for page_type, patterns in TRUST_PATTERNS.items():
        matches = [
            url for url in all_urls
            if any(pattern in url.lower() for pattern in patterns)
        ]

        if matches:
            detected[page_type] = matches[:5]
        else:
            missing.append(page_type)

    if missing:
        findings.append(
            AuditFinding(
                check_id="trust_policy_pages_missing_or_not_discovered",
                category="Trust & Merchant Readiness",
                title="Important trust or policy pages were not discovered",
                status="warning",
                severity="medium",
                confidence="medium",
                affected_urls_count=len(missing),
                evidence=[
                    Evidence(
                        signal="Missing or not discovered",
                        details=page_type,
                    )
                    for page_type in missing
                ],
                recommendation="Ensure key trust pages are present and easy to discover: contact, privacy policy, terms, refund/returns, shipping/delivery, and about pages.",
                business_impact="Trust and policy pages support user confidence and are important for ecommerce and Merchant Center readiness.",
                priority_score=5.0,
            )
        )

    if detected:
        findings.append(
            AuditFinding(
                check_id="trust_policy_pages_detected",
                category="Trust & Merchant Readiness",
                title="Trust and policy pages detected",
                status="pass",
                severity="low",
                confidence="medium",
                affected_urls_count=len(detected),
                evidence=[
                    Evidence(
                        url=urls[0],
                        signal=f"{page_type} page detected",
                        details=", ".join(urls[:3]),
                    )
                    for page_type, urls in detected.items()
                ],
                recommendation="Review detected trust pages for completeness, accuracy, and visibility from footer/navigation.",
                business_impact="Visible trust pages support user confidence and policy compliance.",
                priority_score=1.0,
            )
        )

    return findings