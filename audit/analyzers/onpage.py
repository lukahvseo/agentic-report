from audit.models import AuditFinding, Evidence, PageSignals


def analyze_onpage(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    missing_titles = []
    short_titles = []
    long_titles = []

    missing_meta_descriptions = []
    missing_h1s = []
    multiple_h1s = []

    for page in pages:
        if page.status_code != 200:
            continue

        title = page.title or ""
        meta_description = page.meta_description or ""

        if not title:
            missing_titles.append(page)
        elif len(title) < 20:
            short_titles.append(page)
        elif len(title) > 65:
            long_titles.append(page)

        if not meta_description:
            missing_meta_descriptions.append(page)

        if not page.h1s:
            missing_h1s.append(page)
        elif len(page.h1s) > 1:
            multiple_h1s.append(page)

    if missing_titles:
        findings.append(
            AuditFinding(
                check_id="missing_title_tags",
                category="On-Page SEO",
                title="Missing title tags detected",
                status="fail",
                severity="high",
                confidence="high",
                affected_urls_count=len(missing_titles),
                evidence=[
                    Evidence(url=p.final_url, signal="Missing title tag")
                    for p in missing_titles[:10]
                ],
                recommendation="Add a unique, descriptive title tag to every indexable page.",
                business_impact="Title tags are a major relevance and SERP click-through signal.",
                priority_score=8.0,
            )
        )

    if short_titles:
        findings.append(
            AuditFinding(
                check_id="short_title_tags",
                category="On-Page SEO",
                title="Very short title tags detected",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(short_titles),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Short title tag",
                        details=p.title,
                    )
                    for p in short_titles[:10]
                ],
                recommendation="Rewrite short title tags to better describe the page topic, brand, and search intent.",
                business_impact="Weak titles can reduce relevance and click-through rate.",
                priority_score=5.0,
            )
        )

    if long_titles:
        findings.append(
            AuditFinding(
                check_id="long_title_tags",
                category="On-Page SEO",
                title="Long title tags detected",
                status="warning",
                severity="low",
                confidence="medium",
                affected_urls_count=len(long_titles),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Long title tag",
                        details=p.title,
                    )
                    for p in long_titles[:10]
                ],
                recommendation="Review long title tags and keep the most important terms near the beginning.",
                business_impact="Overly long titles may be truncated in search results.",
                priority_score=3.0,
            )
        )

    if missing_meta_descriptions:
        findings.append(
            AuditFinding(
                check_id="missing_meta_descriptions",
                category="On-Page SEO",
                title="Missing meta descriptions detected",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(missing_meta_descriptions),
                evidence=[
                    Evidence(url=p.final_url, signal="Missing meta description")
                    for p in missing_meta_descriptions[:10]
                ],
                recommendation="Add unique meta descriptions to important indexable pages.",
                business_impact="Meta descriptions can influence search result click-through rate.",
                priority_score=4.5,
            )
        )

    if missing_h1s:
        findings.append(
            AuditFinding(
                check_id="missing_h1_tags",
                category="On-Page SEO",
                title="Missing H1 tags detected",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(missing_h1s),
                evidence=[
                    Evidence(url=p.final_url, signal="Missing H1")
                    for p in missing_h1s[:10]
                ],
                recommendation="Add one clear H1 that describes the primary topic of each page.",
                business_impact="H1s help communicate page topic to users and search engines.",
                priority_score=4.5,
            )
        )

    if multiple_h1s:
        findings.append(
            AuditFinding(
                check_id="multiple_h1_tags",
                category="On-Page SEO",
                title="Multiple H1 tags detected",
                status="warning",
                severity="low",
                confidence="medium",
                affected_urls_count=len(multiple_h1s),
                evidence=[
                    Evidence(
                        url=p.final_url,
                        signal="Multiple H1s",
                        details=" | ".join(p.h1s[:5]),
                    )
                    for p in multiple_h1s[:10]
                ],
                recommendation="Review pages with multiple H1s and use one primary H1 where practical.",
                business_impact="Multiple H1s are not always harmful, but they may weaken page topic clarity.",
                priority_score=3.0,
            )
        )

    if not findings:
        findings.append(
            AuditFinding(
                check_id="basic_onpage_clean",
                category="On-Page SEO",
                title="No major on-page SEO issues detected",
                status="pass",
                severity="low",
                confidence="medium",
                evidence=[],
                affected_urls_count=0,
                recommendation="No major title, meta description, or H1 issues detected in the sampled URLs.",
                business_impact="Sampled pages have basic on-page SEO elements in place.",
                priority_score=1.0,
            )
        )

    return findings