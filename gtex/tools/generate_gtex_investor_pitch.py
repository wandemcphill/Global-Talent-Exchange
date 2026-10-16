from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT = Path("Docs/GTEX_Investor_Pitch.pdf")
THREED_ILLUSTRATION = Path(r"C:\Users\ayomc\Downloads\ChatGPT Image May 3, 2026, 07_45_41 PM.png")


@dataclass(frozen=True)
class Metric:
    label: str
    value: str
    note: str


COLORS = {
    "navy": colors.HexColor("#0B1F33"),
    "navy_2": colors.HexColor("#112B45"),
    "teal": colors.HexColor("#24B7A5"),
    "teal_2": colors.HexColor("#56D4C2"),
    "gold": colors.HexColor("#E1B95A"),
    "gold_2": colors.HexColor("#F3D98C"),
    "green": colors.HexColor("#5CBB79"),
    "red": colors.HexColor("#E46D6D"),
    "ink": colors.HexColor("#102030"),
    "slate": colors.HexColor("#496073"),
    "mist": colors.HexColor("#EAF0F6"),
    "paper": colors.white,
}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "DeckTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=COLORS["paper"],
            alignment=TA_LEFT,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "DeckSubtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=12,
            leading=15,
            textColor=COLORS["mist"],
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "Section",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=COLORS["navy"],
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=COLORS["ink"],
        )
    )
    styles.add(
        ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=COLORS["slate"],
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricValue",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=22,
            textColor=COLORS["navy"],
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=COLORS["slate"],
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricNote",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=COLORS["slate"],
            alignment=TA_CENTER,
        )
    )
    return styles


def _header_footer(canvas, doc):
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFillColor(COLORS["navy"])
    canvas.rect(0, height - 0.42 * inch, width, 0.42 * inch, fill=1, stroke=0)
    canvas.setFillColor(COLORS["mist"])
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(0.55 * inch, height - 0.28 * inch, "GTEX | Global Talent Exchange")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 0.55 * inch, 0.3 * inch, f"Investor pitch | Page {doc.page}")
    canvas.restoreState()


def _title_block(styles):
    story = []
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("GTEX", styles["DeckTitle"]))
    story.append(
        Paragraph(
            "Global Talent Exchange is a football economy operating system: a single product that combines wallet, transfer market, 2D broadcast Match Center, competitions, creator monetization, and admin controls into one backend-authored experience.",
            styles["DeckSubtitle"],
        )
    )
    story.append(
        Paragraph(
            "<b>Investment thesis:</b> GTEX turns football engagement into transaction volume. Every wallet action, transfer, creation, competition entry, and creator payout becomes a revenue event with auditability and strong retention loops.",
            styles["DeckSubtitle"],
        )
    )
    return story


def _metric_table(metrics, styles):
    data = []
    row = []
    for metric in metrics:
        row.append(
            Table(
                [
                    [Paragraph(metric.label, styles["MetricLabel"])],
                    [Paragraph(metric.value, styles["MetricValue"])],
                    [Paragraph(metric.note, styles["MetricNote"])],
                ],
                colWidths=[2.05 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.8, COLORS["mist"]),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, COLORS["mist"]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            )
        )
    data.append(row)
    return Table(
        data,
        colWidths=[2.1 * inch] * len(metrics),
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]),
    )


def _section_header(text):
    d = Drawing(720, 22)
    d.add(Rect(0, 2, 720, 18, fillColor=COLORS["navy"], strokeColor=COLORS["navy"]))
    d.add(String(10, 6, text, fontName="Helvetica-Bold", fontSize=12, fillColor=colors.white))
    return d


def _problem_diagram():
    d = Drawing(720, 170)
    boxes = [
        (
            10,
            55,
            150,
            70,
            "Fragmented football economy",
            "Scouting, wallets, content, competitions, and admin actions live in disconnected tools.",
        ),
        (
            185,
            55,
            150,
            70,
            "No single source of truth",
            "Balances, reserved funds, bids, and payouts are often hard to explain to the user.",
        ),
        (
            360,
            55,
            150,
            70,
            "Low engagement loops",
            "Fans and creators need a live, broadcast-grade surface to stay active.",
        ),
        (
            535,
            55,
            175,
            70,
            "Manual ops overhead",
            "Admins need queues, audits, approvals, and retries instead of spreadsheets.",
        ),
    ]
    for x, y, w, h, title, body in boxes:
        d.add(Rect(x, y, w, h, rx=8, ry=8, fillColor=COLORS["mist"], strokeColor=COLORS["navy_2"], strokeWidth=1))
        d.add(String(x + 10, y + h - 18, title, fontName="Helvetica-Bold", fontSize=10, fillColor=COLORS["navy"]))
        d.add(String(x + 10, y + h - 34, body[:52], fontName="Helvetica", fontSize=7.5, fillColor=COLORS["slate"]))
        d.add(String(x + 10, y + h - 45, body[52:104], fontName="Helvetica", fontSize=7.5, fillColor=COLORS["slate"]))
    for x1, x2 in [(160, 185), (335, 360), (510, 535)]:
        d.add(Line(x1, 90, x2, 90, strokeColor=COLORS["teal"], strokeWidth=2))
    d.add(String(5, 135, "Why GTEX exists", fontName="Helvetica-Bold", fontSize=14, fillColor=COLORS["navy"]))
    return d


def _feature_bars():
    d = Drawing(720, 220)
    bars = VerticalBarChart()
    bars.x = 50
    bars.y = 20
    bars.height = 160
    bars.width = 600
    bars.data = [[92, 88, 86, 84, 81, 78, 76]]
    bars.categoryAxis.categoryNames = [
        "Wallet",
        "Market",
        "Match\nCenter",
        "Competitions",
        "Build-a-Son",
        "Creator",
        "Admin",
    ]
    bars.bars[0].fillColor = COLORS["teal"]
    bars.bars[1].fillColor = COLORS["gold"]
    bars.bars[2].fillColor = COLORS["green"]
    bars.bars[3].fillColor = COLORS["navy_2"]
    bars.bars[4].fillColor = COLORS["teal_2"]
    bars.bars[5].fillColor = COLORS["gold_2"]
    bars.bars[6].fillColor = colors.HexColor("#7A8DA1")
    bars.valueAxis.valueMin = 0
    bars.valueAxis.valueMax = 100
    bars.valueAxis.valueStep = 20
    bars.valueAxis.visibleGrid = 1
    bars.categoryAxis.labels.boxAnchor = "n"
    bars.categoryAxis.labels.dy = -8
    bars.categoryAxis.labels.fontSize = 8
    bars.barWidth = 24
    d.add(
        String(
            5,
            190,
            "Feature stack and readiness by module",
            fontName="Helvetica-Bold",
            fontSize=12,
            fillColor=COLORS["navy"],
        )
    )
    d.add(bars)
    return d


def _pie_chart(title, labels, values, x=40):
    d = Drawing(300, 210)
    pie = Pie()
    pie.x = x
    pie.y = 10
    pie.width = 170
    pie.height = 170
    pie.data = values
    pie.labels = [f"{label}" for label in labels]
    pie.simpleLabels = 0
    pie.sideLabels = 1
    pie.startAngle = 90
    palette = [COLORS["teal"], COLORS["gold"], COLORS["navy_2"], COLORS["green"], COLORS["teal_2"], COLORS["slate"]]
    for idx, _ in enumerate(values):
        pie.slices[idx].fillColor = palette[idx % len(palette)]
        pie.slices[idx].strokeColor = colors.white
        pie.slices[idx].strokeWidth = 1
    d.add(String(0, 190, title, fontName="Helvetica-Bold", fontSize=12, fillColor=COLORS["navy"]))
    d.add(pie)
    return d


def _line_chart():
    d = Drawing(720, 220)
    chart = HorizontalLineChart()
    chart.x = 60
    chart.y = 30
    chart.height = 150
    chart.width = 600
    chart.data = [
        [1.2, 4.8, 14.7],  # Base revenue, USD M
        [8.0, 28.0, 92.0],  # GMV, USD M
    ]
    chart.categoryAxis.categoryNames = ["Year 1", "Year 2", "Year 3"]
    chart.categoryAxis.labels.fontSize = 9
    chart.categoryAxis.labels.fillColor = COLORS["slate"]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 20
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.visibleGrid = 1
    chart.lines[0].strokeColor = COLORS["teal"]
    chart.lines[0].strokeWidth = 2.5
    chart.lines[1].strokeColor = COLORS["gold"]
    chart.lines[1].strokeWidth = 2.5
    chart.lines[0].symbol = makeMarker("Circle")
    chart.lines[1].symbol = makeMarker("Square")
    chart.lines[0].symbol.size = 6
    chart.lines[1].symbol.size = 6
    d.add(
        String(
            5,
            190,
            "Illustrative 3-year base case: revenue and GMV growth",
            fontName="Helvetica-Bold",
            fontSize=12,
            fillColor=COLORS["navy"],
        )
    )
    d.add(chart)
    return d


def _projection_table():
    data = [
        ["Metric", "Year 1", "Year 2", "Year 3"],
        ["MAU", "250k", "750k", "1.8M"],
        ["Transacting MAU", "30k", "135k", "396k"],
        ["GMV", "$8.0M", "$28.0M", "$92.0M"],
        ["Blended take rate", "4.5%", "4.6%", "4.8%"],
        ["Revenue", "$1.2M", "$4.8M", "$14.7M"],
        ["EBITDA margin", "-12%", "14%", "33%"],
    ]
    table = Table(
        data,
        colWidths=[2.0 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["navy"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, COLORS["mist"]),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLORS["mist"]]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        ),
    )
    return table


def _use_of_funds_pie():
    return _pie_chart(
        "Use of funds in a $2.5M seed round",
        ["Product/Engineering", "Growth", "Ops/Compliance", "Liquidity", "Data/Infra"],
        [40, 25, 15, 10, 10],
        x=55,
    )


def _three_d_revenue_pie():
    return _pie_chart(
        "3D/gamers/streamer monetization mix",
        ["Season passes", "Cosmetics", "Streamer tournaments", "Ads/sponsorships", "Marketplace", "UGC shares"],
        [26, 18, 17, 15, 14, 10],
        x=48,
    )


def _fit_image(path: Path, max_width: float, max_height: float):
    reader = ImageReader(str(path))
    width, height = reader.getSize()
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def build_pdf(output: Path = OUTPUT) -> Path:
    styles = _styles()
    doc = SimpleDocTemplate(
        str(output),
        pagesize=landscape(letter),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.5 * inch,
        title="GTEX Investor Pitch",
        author="Codex",
        subject="GTEX investor pitch",
    )

    story = []

    # Cover / executive summary
    story.extend(_title_block(styles))
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        Table(
            [
                [
                    Paragraph(
                        "<b>Problem</b><br/>Football discovery, engagement, and financial operations are fragmented across tools.",
                        styles["Body"],
                    ),
                    Paragraph(
                        "<b>Solution</b><br/>GTEX unifies wallet, market, match center, competitions, creators, and admin into one platform.",
                        styles["Body"],
                    ),
                    Paragraph(
                        "<b>Business model</b><br/>Transaction fees, market commissions, competition fees, creation fees, creator monetization, and premium admin tools.",
                        styles["Body"],
                    ),
                ]
            ],
            colWidths=[3.0 * inch, 3.0 * inch, 3.0 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.8, COLORS["mist"]),
                    ("GRID", (0, 0), (-1, -1), 0.5, COLORS["mist"]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            ),
        )
    )
    story.append(Spacer(1, 0.12 * inch))
    metrics = [
        Metric("3-year revenue", "$14.7M", "Base case, conservative take rates"),
        Metric("3-year GMV", "$92.0M", "Transfer + wallet + competition volume"),
        Metric("Blended take rate", "4.8%", "Across market, wallet, creation, events"),
        Metric("Seed ask", "$2.5M", "Product, growth, operations, launch readiness"),
    ]
    story.append(_metric_table(metrics, styles))
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        Paragraph(
            "<b>Investor summary:</b> GTEX is not just a fan app. It is a transaction engine for football economies, with backend-authored truth for wallets, bids, match events, creator payouts, and competition settlement.",
            styles["Body"],
        )
    )
    story.append(PageBreak())

    # Problem
    story.append(_section_header("1. The Problem GTEX Solves"))
    story.append(Spacer(1, 0.12 * inch))
    story.append(_problem_diagram())
    story.append(Spacer(1, 0.15 * inch))
    problem_rows = [
        ["Pain point", "What it costs the market"],
        [
            "Fragmented discovery",
            "Scouts, owners, and fans use disconnected tools, so talent and opportunity are missed.",
        ],
        ["Opaque finance", "Wallet, transfer, and payout truth is hard to explain and easy to dispute."],
        ["Weak retention", "Football apps often lack a daily operating loop beyond watching scores."],
        ["Manual admin burden", "Approvals, disputes, settlement, and reconciliation consume staff time."],
    ]
    story.append(
        Table(
            problem_rows,
            colWidths=[1.9 * inch, 6.9 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLORS["navy"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, COLORS["mist"]),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLORS["mist"]]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        )
    )
    story.append(PageBreak())

    # Product
    story.append(_section_header("2. GTEX Product Stack"))
    story.append(Spacer(1, 0.12 * inch))
    story.append(_feature_bars())
    story.append(Spacer(1, 0.16 * inch))
    product_rows = [
        ["Feature", "What it does", "Why it matters"],
        [
            "Wallet",
            "Available, reserved, locked, pending balances with clear ledger states",
            "Makes money movement understandable and auditable",
        ],
        [
            "Transfer Market",
            "Live listings, bids, counters, reservations, settlement",
            "Creates transaction frequency and network effects",
        ],
        [
            "2D Match Center",
            "Broadcast-style match viewing with score, commentary, stats, and overlays",
            "Drives retention and daily engagement",
        ],
        [
            "Build-a-Son",
            "Regeneration and player creation flow with backend-derived projections",
            "Creates premium creation revenue and emotional attachment",
        ],
        [
            "Competitions",
            "Bracket/league lifecycle with entry and payout flows",
            "Generates event-driven monetization and repeat play",
        ],
        [
            "Creator / Community",
            "Content and creator monetization surface with admin oversight",
            "Adds another monetized engagement loop",
        ],
        [
            "Admin Command Center",
            "Queues, approvals, exports, audits, and operator controls",
            "Keeps the platform safe at scale",
        ],
    ]
    story.append(
        Table(
            product_rows,
            colWidths=[1.3 * inch, 4.65 * inch, 2.9 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLORS["navy"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.45, COLORS["mist"]),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLORS["mist"]]),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )
    )
    story.append(PageBreak())

    # Monetization
    story.append(_section_header("3. Monetization Engine"))
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        Table(
            [
                [
                    _pie_chart(
                        "Illustrative 2028 revenue mix",
                        [
                            "Transfer fees",
                            "Wallet / payout fees",
                            "Competition fees",
                            "Build-a-Son",
                            "Creator share",
                            "Premium ops",
                        ],
                        [35, 20, 15, 12, 10, 8],
                        x=45,
                    ),
                    Paragraph(
                        "<b>How GTEX makes money</b><br/><br/>"
                        "1. Transfer market commissions on player transactions.<br/>"
                        "2. Wallet and withdrawal spreads/fees where permitted.<br/>"
                        "3. Build-a-Son creation fees and premium progression upgrades.<br/>"
                        "4. Competition entry and hosting fees.<br/>"
                        "5. Creator monetization and content revenue share.<br/>"
                        "6. Premium admin, club, and operator tooling.<br/><br/>"
                        "<b>Logic:</b> each feature creates either a transaction, an upgrade, or a premium workflow. That gives GTEX multiple non-overlapping revenue streams and reduces dependence on one monetization mode.",
                        styles["Body"],
                    ),
                ]
            ],
            colWidths=[3.5 * inch, 5.3 * inch],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
        )
    )
    story.append(Spacer(1, 0.12 * inch))
    monetization_rows = [
        ["Revenue stream", "Example fee model", "Base-case annual revenue by Year 3"],
        ["Transfer market", "4% commission on GMV", "$3.2M"],
        ["Wallet / payouts", "1% net spread / withdrawal fee", "$1.8M"],
        ["Competitions", "Entry + hosted event fees", "$2.4M"],
        ["Build-a-Son", "Fixed creation fee + upgrade upsell", "$1.7M"],
        ["Creator monetization", "Platform share on clip revenue", "$1.4M"],
        ["Premium admin / ops", "B2B dashboard licensing / support", "$4.2M"],
    ]
    story.append(
        Table(
            monetization_rows,
            colWidths=[2.1 * inch, 2.7 * inch, 2.6 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLORS["navy"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.45, COLORS["mist"]),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLORS["mist"]]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )
    )
    story.append(PageBreak())

    # Growth and figures
    story.append(_section_header("4. Growth and Financial Outlook"))
    story.append(Spacer(1, 0.12 * inch))
    story.append(_line_chart())
    story.append(Spacer(1, 0.14 * inch))
    story.append(_projection_table())
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        Paragraph(
            "<b>Interpretation:</b> the base case assumes GTEX grows from a focused beta into a multi-module transaction platform. Revenue scales faster than MAU because transacting users, transfer volume, competition activity, and creator payouts compound across the same customer base.",
            styles["Body"],
        )
    )
    story.append(PageBreak())

    # Future 3D / gamer and streamer monetization appendix
    story.append(_section_header("5. Future 3D Match Engine and Gamer Monetization"))
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        Paragraph(
            "GTEX can add a premium 3D match engine as an eventual expansion layer for gamers, streamers, and esports-style leagues. In this model, the 3D module is not the core operating system; it is a monetized engagement engine that sits on top of the football economy.",
            styles["Body"],
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    if THREED_ILLUSTRATION.exists():
        story.append(
            _fit_image(
                THREED_ILLUSTRATION,
                max_width=9.15 * inch,
                max_height=4.6 * inch,
            )
        )
        story.append(Spacer(1, 0.05 * inch))
        story.append(
            Paragraph(
                "Figure: GTEX 3D match engine illustration provided by the founder. This is the visual direction for a higher-fidelity gameplay layer.",
                styles["Small"],
            )
        )
    else:
        story.append(Paragraph("Illustration missing from expected Downloads path.", styles["Small"]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        Table(
            [
                [
                    _three_d_revenue_pie(),
                    Paragraph(
                        "<b>How the 3D layer makes money</b><br/><br/>"
                        "• <b>Season pass / battle pass:</b> unlocks ranked seasons, cosmetics, and premium progression.<br/>"
                        "• <b>Cosmetics:</b> kits, boots, stadium themes, celebrations, commentary packs, and avatar items.<br/>"
                        "• <b>Streamer tournaments:</b> entry fees, featured brackets, spectator boosts, and sponsored showmatches.<br/>"
                        "• <b>Creator monetization:</b> revenue share from streamed 3D clips, highlights, and event sponsorships.<br/>"
                        "• <b>Marketplace fees:</b> trade fees on collectible items, player skins, and season badges.<br/>"
                        "• <b>Ads and sponsorships:</b> branded overlays, stadium boards, and season sponsorship packages.<br/><br/>"
                        "<b>Why it works:</b> gamers spend for status and progression, streamers spend for audience hooks, and sponsors pay for repeat live attention. The 3D layer monetizes entertainment while the core GTEX economy monetizes football transactions.",
                        styles["Body"],
                    ),
                ]
            ],
            colWidths=[3.2 * inch, 5.5 * inch],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
        )
    )
    story.append(Spacer(1, 0.12 * inch))
    threed_rows = [
        ["3D stream", "Example price point", "Illustrative annual revenue"],
        ["Season pass and progression", "$9.99-$19.99 per season", "$1.8M"],
        ["Cosmetics and avatar items", "$2-$25 microtransactions", "$2.6M"],
        ["Streamer tournaments and showmatches", "$25-$250 entry/sponsorship packages", "$1.9M"],
        ["Ads, branded overlays, sponsorships", "Campaign contracts", "$2.4M"],
        ["UGC and clip revenue share", "Platform share on monetized clips", "$1.1M"],
        ["Marketplace fees on items", "2%-8% fee on trades", "$1.5M"],
    ]
    story.append(
        Table(
            threed_rows,
            colWidths=[2.1 * inch, 2.6 * inch, 2.8 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLORS["navy"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.45, COLORS["mist"]),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLORS["mist"]]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )
    )
    story.append(PageBreak())

    # Funds / moat
    story.append(_section_header("6. Use of Funds and Moat"))
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        Table(
            [
                [
                    _use_of_funds_pie(),
                    Paragraph(
                        "<b>Why GTEX can win</b><br/><br/>"
                        "• The product has a strong system moat: wallet, market, competition, match center, and creator loops reinforce one another.<br/>"
                        "• Backend-authored truth keeps balances, bids, and results auditable.<br/>"
                        "• The 2D broadcast Match Center creates daily engagement without needing expensive simulation-heavy infrastructure.<br/>"
                        "• Admin command centers and queues reduce operational friction as volume grows.<br/><br/>"
                        "<b>Use of a $2.5M seed:</b> finish product depth, harden money paths, add analytics/observability, and fund launch acquisition.<br/><br/>"
                        "This is an illustrative deck, not audited financial advice. Real outcomes depend on product execution, market timing, and regulatory compliance.",
                        styles["Body"],
                    ),
                ]
            ],
            colWidths=[3.2 * inch, 5.6 * inch],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    final_rows = [
        ["Investor ask", "Use of funds", "Milestone target"],
        [
            "$2.5M seed",
            "Product + growth + ops + compliance",
            "Launch-ready GTEX with monetized transaction rails and a trusted 2D match center",
        ],
    ]
    story.append(
        Table(
            final_rows,
            colWidths=[1.5 * inch, 4.2 * inch, 3.4 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLORS["navy"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.45, COLORS["mist"]),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLORS["mist"]]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            ),
        )
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output


if __name__ == "__main__":
    path = build_pdf()
    print(path.resolve())
