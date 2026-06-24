from uuid import uuid4

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from audit.models import AuditFinding, Evidence
from audit.runner import run_audit
from audit.collectors.shopping_serp import check_visibility_for_keywords
from audit.analyzers.shopping_visibility import build_shopping_findings_from_result
from audit.reporting.html_pdf import generate_pdf_from_html

import os

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


app = FastAPI(title="Agentic Report")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

REPORT_STORE = {}


def calculate_summary(result):
    findings = result.findings

    fails = len([f for f in findings if f.status == "fail"])
    warnings = len([f for f in findings if f.status == "warning"])
    passes = len([f for f in findings if f.status == "pass"])
    unknown = len([f for f in findings if f.status == "unknown"])

    critical = len([f for f in findings if f.severity == "critical"])
    high = len([f for f in findings if f.severity == "high"])
    medium = len([f for f in findings if f.severity == "medium"])
    low = len([f for f in findings if f.severity == "low"])

    score = 100
    score -= critical * 20
    score -= high * 12
    score -= medium * 6
    score -= low * 2
    score = max(0, min(100, score))

    return {
        "total": len(findings),
        "fails": fails,
        "warnings": warnings,
        "passes": passes,
        "unknown": unknown,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "score": score,
    }


def parse_textarea_lines(text: str) -> list[str]:
    lines = []

    for line in text.splitlines():
        clean = line.strip()

        if not clean:
            continue

        if clean.startswith("#"):
            continue

        lines.append(clean)

    return lines


def make_default_shopping_summary():
    return {
        "status": "skipped",
        "message": "Shopping visibility check was not run.",
        "shopping_tab_score": None,
        "price_coverage_score": None,
        "review_coverage_score": None,
        "rows": [],
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {},
    )


@app.post("/audit", response_class=HTMLResponse)
async def audit(
    request: Request,
    url: str = Form(...),
    crawl_mode: str = Form("manual"),
    manual_urls_text: str = Form(""),
    merchant_name: str = Form(""),
    shopping_keywords_text: str = Form(""),
    shopping_location: str = Form(""),
    shopping_country: str = Form("us"),
    shopping_language: str = Form("en"),
):
    manual_urls = parse_textarea_lines(manual_urls_text)
    shopping_keywords = parse_textarea_lines(shopping_keywords_text)

    result = await run_audit(
        url=url,
        max_pages=5,
        manual_urls=manual_urls,
        crawl_mode=crawl_mode,
    )

    shopping_summary = make_default_shopping_summary()

    serpapi_key_is_configured = (
        SERPAPI_KEY
        and SERPAPI_KEY.strip()
        and SERPAPI_KEY != "PASTE_YOUR_SERPAPI_KEY_HERE"
    )

    if not serpapi_key_is_configured:
        shopping_summary = {
            "status": "not_configured",
            "message": "Shopping visibility check skipped because SerpApi key is not configured in web_app.py.",
            "shopping_tab_score": None,
            "price_coverage_score": None,
            "review_coverage_score": None,
            "rows": [],
        }

    elif not shopping_keywords:
        shopping_summary = {
            "status": "no_keywords",
            "message": "Shopping visibility check skipped because no Shopping Keywords were entered.",
            "shopping_tab_score": None,
            "price_coverage_score": None,
            "review_coverage_score": None,
            "rows": [],
        }

    else:
        try:
            shopping_result = check_visibility_for_keywords(
                domain=url,
                api_key=SERPAPI_KEY,
                merchant_name=merchant_name.strip(),
                keywords=shopping_keywords,
                location=shopping_location.strip(),
                gl=shopping_country.strip() or "us",
                hl=shopping_language.strip() or "en",
                google_domain="google.com",
            )

            shopping_summary = {
                "status": "ran",
                "message": "Shopping visibility check completed.",
                "shopping_tab_score": shopping_result.get("shopping_tab_score"),
                "price_coverage_score": shopping_result.get("price_coverage_score"),
                "review_coverage_score": shopping_result.get("review_coverage_score"),
                "rows": shopping_result.get("shopping_tab_rows", []),
            }

            shopping_findings = build_shopping_findings_from_result(shopping_result)

            result.findings.extend(shopping_findings)
            result.findings = sorted(
                result.findings,
                key=lambda finding: finding.priority_score,
                reverse=True,
            )

        except Exception as error:
            shopping_summary = {
                "status": "error",
                "message": f"Shopping visibility check failed: {error}",
                "shopping_tab_score": None,
                "price_coverage_score": None,
                "review_coverage_score": None,
                "rows": [],
            }

            result.findings.append(
                AuditFinding(
                    check_id="shopping_visibility_api_error",
                    category="Search Results Visibility",
                    title="Shopping visibility check failed",
                    status="unknown",
                    severity="medium",
                    confidence="low",
                    affected_urls_count=0,
                    evidence=[
                        Evidence(
                            signal="SerpApi error",
                            details=str(error),
                        )
                    ],
                    recommendation="Check the SerpApi key, keyword inputs, country/language settings, and API account limits.",
                    business_impact="Shopping visibility could not be evaluated for this report.",
                    priority_score=4.0,
                )
            )

            result.findings = sorted(
                result.findings,
                key=lambda finding: finding.priority_score,
                reverse=True,
            )

    summary = calculate_summary(result)

    report_id = str(uuid4())

    REPORT_STORE[report_id] = {
        "result": result,
        "summary": summary,
        "shopping_summary": shopping_summary,
    }

    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "result": result,
            "summary": summary,
            "top_findings": result.findings[:8],
            "shopping_summary": shopping_summary,
            "report_id": report_id,
        },
    )


@app.get("/reports/{report_id}/pdf")
async def export_pdf(report_id: str):
    report_data = REPORT_STORE.get(report_id)

    if not report_data:
        return Response(
            content="Report not found. Please run the audit again.",
            status_code=404,
            media_type="text/plain",
        )

    template = templates.env.get_template("report.html")

    html = template.render(
        result=report_data["result"],
        summary=report_data["summary"],
        top_findings=report_data["result"].findings[:8],
        shopping_summary=report_data["shopping_summary"],
        report_id=report_id,
        pdf_mode=True,
    )

    pdf_bytes = await generate_pdf_from_html(html)

    safe_filename = (
        report_data["result"]
        .input_url.replace("https://", "")
        .replace("http://", "")
        .replace("/", "_")
        .replace(":", "_")
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}_agentic_report.pdf"'
        },
    )