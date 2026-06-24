from audit.models import AuditFinding, Evidence, PageSignals


def analyze_tracking(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    html_pages = [p for p in pages if p.status_code == 200]

    all_tracking = sorted(
        set(
            signal
            for page in html_pages
            for signal in page.tracking_signals
        )
    )

    pages_without_tracking = [
        p for p in html_pages
        if not p.tracking_signals
    ]

    if all_tracking:
        findings.append(
            AuditFinding(
                check_id="tracking_detected",
                category="Tracking & Measurement",
                title="Tracking scripts detected",
                status="pass",
                severity="low",
                confidence="medium",
                affected_urls_count=len(html_pages) - len(pages_without_tracking),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Tracking detected",
                        details=", ".join(p.tracking_signals),
                    )
                    for p in html_pages
                    if p.tracking_signals
                ][:10],
                recommendation="Validate that tracking events fire correctly for key actions such as form submissions, add-to-cart, checkout, and purchases.",
                business_impact=f"Detected tracking systems: {', '.join(all_tracking)}",
                priority_score=1.0,
            )
        )
    else:
        findings.append(
            AuditFinding(
                check_id="tracking_not_detected",
                category="Tracking & Measurement",
                title="No common tracking scripts detected",
                status="warning",
                severity="medium",
                confidence="medium",
                affected_urls_count=len(html_pages),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="No common tracking scripts detected",
                    )
                    for p in html_pages[:10]
                ],
                recommendation="Confirm whether GA4, Google Tag Manager, Google Ads, or other analytics/conversion tracking is installed.",
                business_impact="Without reliable tracking, SEO, Shopping, and conversion performance are harder to measure.",
                priority_score=5.0,
            )
        )

    return findings