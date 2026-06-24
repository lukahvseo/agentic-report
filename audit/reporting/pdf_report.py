from io import BytesIO
from html import escape
from urllib.parse import urlparse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BRAND_ORANGE = colors.HexColor("#f97316")
BRAND_DARK = colors.HexColor("#111827")
BRAND_MUTED = colors.HexColor("#64748b")
BRAND_BORDER = colors.HexColor("#e5e7eb")
BRAND_BG = colors.HexColor("#fff7ed")
SUCCESS = colors.HexColor("#16a34a")
WARNING = colors.HexColor("#d97706")
DANGER = colors.HexColor("#dc2626")
UNKNOWN = colors.HexColor("#64748b")


class Badge(Flowable):
    def __init__(self, text, fill_color, text_color=colors.white, width=34 * mm, height=8 * mm):
        super().__init__()
        self.text = str(text).upper()
        self.fill_color = fill_color
        self.text_color = text_color
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(0, 0, self.width, self.height, 3 * mm, fill=1, stroke=0)
        self.canv.setFillColor(self.text_color)
        self.canv.setFont("Helvetica-Bold", 7)
        self.canv.drawCentredString(self.width / 2, 2.6 * mm, self.text)


def clean_text(value, max_length=None):
    if value is None:
        return "-"

    text = str(value)
    text = text.replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())

    if max_length and len(text) > max_length:
        return text[: max_length - 1] + "..."

    return text


def p(value, style):
    return Paragraph(escape(clean_text(value)), style)


def status_color(status):
    if status == "pass":
        return SUCCESS
    if status == "warning":
        return WARNING
    if status == "fail":
        return DANGER
    return UNKNOWN


def severity_color(severity):
    if severity in ["critical", "high"]:
        return DANGER
    if severity == "medium":
        return WARNING
    return UNKNOWN


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawString(16 * mm, 10 * mm, "Agentic Report - Ecommerce Audit")
    canvas.drawRightString(194 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_score_card(summary, styles):
    data = [
        [
            p("Audit Score", styles["MetricLabel"]),
            p("Fails", styles["MetricLabel"]),
            p("Warnings", styles["MetricLabel"]),
            p("Passed", styles["MetricLabel"]),
            p("Findings", styles["MetricLabel"]),
        ],
        [
            p(str(summary.get("score", 0)), styles["MetricValueOrange"]),
            p(str(summary.get("fails", 0)), styles["MetricValueDanger"]),
            p(str(summary.get("warnings", 0)), styles["MetricValueWarning"]),
            p(str(summary.get("passes", 0)), styles["MetricValueSuccess"]),
            p(str(summary.get("total", 0)), styles["MetricValue"]),
        ],
    ]

    table = Table(data, colWidths=[34 * mm, 32 * mm, 32 * mm, 32 * mm, 32 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, BRAND_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BRAND_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return table


def build_shopping_section(shopping_summary, styles):
    elements = []

    elements.append(Paragraph("Google Shopping Visibility", styles["SectionTitle"]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(clean_text(shopping_summary.get("message")), styles["Body"]))

    if shopping_summary.get("status") != "ran":
        elements.append(Spacer(1, 5 * mm))
        return elements

    metric_data = [
        [
            p("Shopping Visibility", styles["MetricLabel"]),
            p("Price Coverage", styles["MetricLabel"]),
            p("Review Coverage", styles["MetricLabel"]),
            p("Queries", styles["MetricLabel"]),
        ],
        [
            p(f"{shopping_summary.get('shopping_tab_score')}%", styles["MetricValueOrange"]),
            p(f"{shopping_summary.get('price_coverage_score')}%", styles["MetricValue"]),
            p(f"{shopping_summary.get('review_coverage_score')}%", styles["MetricValue"]),
            p(str(len(shopping_summary.get("rows", []))), styles["MetricValue"]),
        ],
    ]

    metric_table = Table(metric_data, colWidths=[40 * mm, 40 * mm, 40 * mm, 40 * mm])
    metric_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, BRAND_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BRAND_BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    elements.append(Spacer(1, 5 * mm))
    elements.append(metric_table)
    elements.append(Spacer(1, 5 * mm))

    rows = shopping_summary.get("rows", [])

    table_data = [
        [
            p("Query", styles["TableHeader"]),
            p("Found", styles["TableHeader"]),
            p("Pos.", styles["TableHeader"]),
            p("Title / Merchant", styles["TableHeader"]),
            p("Price", styles["TableHeader"]),
            p("Reviews", styles["TableHeader"]),
        ]
    ]

    for row in rows[:12]:
        found = "Yes" if row.get("found_on_shopping_tab") else "No"
        title = clean_text(row.get("matched_title") or "-", 75)
        merchant = clean_text(row.get("merchant") or "-", 45)
        title_merchant = f"{title}<br/><font color='#64748b'>{merchant}</font>"

        table_data.append(
            [
                p(row.get("query"), styles["TableCell"]),
                p(found, styles["TableCell"]),
                p(row.get("position") or "-", styles["TableCell"]),
                Paragraph(title_merchant, styles["TableCell"]),
                p(row.get("price") or "-", styles["TableCell"]),
                p(row.get("reviews") or "-", styles["TableCell"]),
            ]
        )

    table = Table(
        table_data,
        colWidths=[38 * mm, 16 * mm, 12 * mm, 68 * mm, 22 * mm, 22 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_DARK),
                ("BOX", (0, 0), (-1, -1), 0.7, BRAND_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, BRAND_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 6 * mm))

    return elements


def build_finding_card(finding, styles):
    status_badge = Badge(finding.status, status_color(finding.status), width=24 * mm)
    severity_badge = Badge(finding.severity, severity_color(finding.severity), width=24 * mm)

    badge_table = Table([[status_badge, severity_badge]], colWidths=[27 * mm, 27 * mm])
    badge_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    evidence_lines = []

    for evidence in finding.evidence[:3]:
        line = f"<b>{escape(clean_text(evidence.signal, 80))}</b>"

        if evidence.url:
            line += f"<br/><font color='#64748b'>{escape(clean_text(evidence.url, 110))}</font>"

        if evidence.details:
            line += f"<br/>{escape(clean_text(evidence.details, 180))}"

        evidence_lines.append(Paragraph(line, styles["Small"]))

    inner = [
        badge_table,
        Spacer(1, 2 * mm),
        Paragraph(escape(clean_text(finding.title, 140)), styles["FindingTitle"]),
        Paragraph(escape(clean_text(finding.category)), styles["Category"]),
        Spacer(1, 2 * mm),
        Paragraph(
            f"<b>Impact:</b> {escape(clean_text(finding.business_impact, 260))}",
            styles["Body"],
        ),
        Paragraph(
            f"<b>Recommendation:</b> {escape(clean_text(finding.recommendation, 360))}",
            styles["Body"],
        ),
    ]

    if evidence_lines:
        inner.append(Spacer(1, 2 * mm))
        inner.append(Paragraph("<b>Evidence:</b>", styles["Small"]))
        inner.extend(evidence_lines)

    wrapper = Table([[inner]], colWidths=[178 * mm])
    wrapper.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, BRAND_BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    return KeepTogether([wrapper, Spacer(1, 4 * mm)])


def generate_pdf_report(result, summary, shopping_summary) -> bytes:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Agentic Report",
    )

    sample_styles = getSampleStyleSheet()

    styles = {
        "Title": ParagraphStyle(
            "Title",
            parent=sample_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=BRAND_DARK,
            alignment=TA_LEFT,
            spaceAfter=4 * mm,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=BRAND_MUTED,
            spaceAfter=6 * mm,
        ),
        "SectionTitle": ParagraphStyle(
            "SectionTitle",
            parent=sample_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=BRAND_DARK,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        ),
        "FindingTitle": ParagraphStyle(
            "FindingTitle",
            parent=sample_styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=BRAND_DARK,
            spaceAfter=1 * mm,
        ),
        "Category": ParagraphStyle(
            "Category",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=BRAND_ORANGE,
            spaceAfter=2 * mm,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=BRAND_DARK,
            spaceAfter=1.5 * mm,
        ),
        "Small": ParagraphStyle(
            "Small",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=BRAND_DARK,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=BRAND_DARK,
            alignment=TA_LEFT,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=BRAND_DARK,
        ),
        "MetricLabel": ParagraphStyle(
            "MetricLabel",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=BRAND_MUTED,
            alignment=TA_CENTER,
        ),
        "MetricValue": ParagraphStyle(
            "MetricValue",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=BRAND_DARK,
            alignment=TA_CENTER,
        ),
        "MetricValueOrange": ParagraphStyle(
            "MetricValueOrange",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=20,
            textColor=BRAND_ORANGE,
            alignment=TA_CENTER,
        ),
        "MetricValueDanger": ParagraphStyle(
            "MetricValueDanger",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=DANGER,
            alignment=TA_CENTER,
        ),
        "MetricValueWarning": ParagraphStyle(
            "MetricValueWarning",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=WARNING,
            alignment=TA_CENTER,
        ),
        "MetricValueSuccess": ParagraphStyle(
            "MetricValueSuccess",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=SUCCESS,
            alignment=TA_CENTER,
        ),
    }

    elements = []

    domain = urlparse(result.input_url).netloc or result.input_url

    header_table = Table(
        [
            [
                Paragraph("<b>HV</b>", ParagraphStyle(
                    "LogoText",
                    fontName="Helvetica-Bold",
                    fontSize=15,
                    leading=17,
                    textColor=colors.white,
                    alignment=TA_CENTER,
                )),
                [
                    Paragraph("Agentic Report", styles["Title"]),
                    Paragraph(
                        f"Ecommerce audit for {escape(clean_text(domain))}",
                        styles["Subtitle"],
                    ),
                ],
            ]
        ],
        colWidths=[16 * mm, 162 * mm],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), BRAND_ORANGE),
                ("BOX", (0, 0), (0, 0), 0, BRAND_ORANGE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 0),
                ("TOPPADDING", (0, 0), (0, 0), 8),
                ("BOTTOMPADDING", (0, 0), (0, 0), 8),
            ]
        )
    )

    elements.append(header_table)
    elements.append(Spacer(1, 5 * mm))

    elements.append(
        Paragraph(
            f"<b>Input URL:</b> {escape(clean_text(result.input_url, 160))}<br/>"
            f"<b>Final URL:</b> {escape(clean_text(result.final_url, 160))}<br/>"
            f"<b>Pages checked:</b> {result.pages_checked}",
            styles["Body"],
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(build_score_card(summary, styles))
    elements.append(Spacer(1, 6 * mm))

    elements.extend(build_shopping_section(shopping_summary, styles))

    elements.append(Paragraph("Top Findings", styles["SectionTitle"]))
    elements.append(Spacer(1, 2 * mm))

    for finding in result.findings[:8]:
        elements.append(build_finding_card(finding, styles))

    elements.append(PageBreak())
    elements.append(Paragraph("Detailed Findings", styles["SectionTitle"]))

    detailed_data = [
        [
            p("Status", styles["TableHeader"]),
            p("Severity", styles["TableHeader"]),
            p("Category", styles["TableHeader"]),
            p("Finding", styles["TableHeader"]),
            p("Affected", styles["TableHeader"]),
        ]
    ]

    for finding in result.findings:
        detailed_data.append(
            [
                p(finding.status, styles["TableCell"]),
                p(finding.severity, styles["TableCell"]),
                p(finding.category, styles["TableCell"]),
                p(finding.title, styles["TableCell"]),
                p(str(finding.affected_urls_count), styles["TableCell"]),
            ]
        )

    detailed_table = Table(
        detailed_data,
        colWidths=[22 * mm, 22 * mm, 42 * mm, 78 * mm, 14 * mm],
        repeatRows=1,
    )
    detailed_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_BG),
                ("BOX", (0, 0), (-1, -1), 0.7, BRAND_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, BRAND_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.append(detailed_table)
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph("Sampled Pages", styles["SectionTitle"]))

    pages_data = [
        [
            p("Status", styles["TableHeader"]),
            p("Type", styles["TableHeader"]),
            p("URL", styles["TableHeader"]),
            p("Title", styles["TableHeader"]),
            p("Schema", styles["TableHeader"]),
        ]
    ]

    for page in result.page_signals:
        pages_data.append(
            [
                p(str(page.status_code), styles["TableCell"]),
                p(page.page_type or "unknown", styles["TableCell"]),
                p(page.final_url, styles["TableCell"]),
                p(page.title or "-", styles["TableCell"]),
                p(", ".join(page.schema_types) if page.schema_types else "-", styles["TableCell"]),
            ]
        )

    pages_table = Table(
        pages_data,
        colWidths=[16 * mm, 24 * mm, 64 * mm, 50 * mm, 24 * mm],
        repeatRows=1,
    )
    pages_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_BG),
                ("BOX", (0, 0), (-1, -1), 0.7, BRAND_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, BRAND_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.append(pages_table)

    doc.build(
        elements,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes