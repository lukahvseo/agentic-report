import asyncio
from pathlib import Path

from playwright.sync_api import sync_playwright


def _generate_pdf_from_html_sync(html: str) -> bytes:
    css_path = Path("static/css/styles.css")

    css = ""
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")

    pdf_extra_css = """
      <style>
        body {
          background:
            radial-gradient(circle at top left, rgba(249, 115, 22, 0.14), transparent 36%),
            #f8fafc !important;
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }

        .report-actions {
          display: none !important;
        }

        .report-shell {
          width: min(1180px, calc(100% - 40px)) !important;
          padding: 24px 0 56px !important;
        }

        .section-card,
        .finding-card,
        .score-card,
        .stat-card,
        .audit-card {
          break-inside: avoid;
          page-break-inside: avoid;
        }

        .section-card {
          margin-top: 18px !important;
        }

        .report-header {
          margin-bottom: 28px !important;
        }

        .report-hero {
          margin-bottom: 20px !important;
        }

        .hero-copy h1,
        .report-hero h1 {
          font-size: 38px !important;
          line-height: 1.02 !important;
        }

        .score-number {
          font-size: 58px !important;
        }

        .stats-grid {
          gap: 12px !important;
          margin: 20px 0 !important;
        }

        .stat-card {
          padding: 16px !important;
        }

        .stat-card strong {
          font-size: 28px !important;
        }

        .section-card {
          padding: 22px !important;
        }

        .finding-card {
          padding: 18px !important;
        }

        details {
          display: block !important;
        }

        details > summary {
          font-weight: 900;
        }

        table {
          page-break-inside: auto;
        }

        tr {
          page-break-inside: avoid;
          page-break-after: auto;
        }

        th,
        td {
          font-size: 12px !important;
          padding: 10px 12px !important;
        }

        a {
          color: #f97316 !important;
        }

        @page {
          size: A4;
          margin: 10mm;
        }
      </style>
    """

    html = html.replace(
        '<link rel="stylesheet" href="/static/css/styles.css" />',
        f"<style>{css}</style>{pdf_extra_css}",
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 1600,
            },
            device_scale_factor=1,
        )

        page.set_content(
            html,
            wait_until="networkidle",
        )

        page.emulate_media(media="screen")

        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={
                "top": "10mm",
                "right": "8mm",
                "bottom": "10mm",
                "left": "8mm",
            },
        )

        browser.close()

    return pdf_bytes


async def generate_pdf_from_html(html: str) -> bytes:
    return await asyncio.to_thread(_generate_pdf_from_html_sync, html)