from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.colors import HexColor  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_LEFT  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = HexColor("#123047")
TEAL = HexColor("#1E8A8A")
GREY = HexColor("#586875")
LIGHT_GREY = HexColor("#EEF3F5")


def _register_fonts() -> tuple[str, str]:
    font_dir = Path(__file__).with_name("fonts")
    regular = font_dir / "Lato-Regular.ttf"
    bold = font_dir / "Lato-Bold.ttf"
    if regular.exists() and bold.exists():
        if "Lato" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("Lato", regular))
            pdfmetrics.registerFont(TTFont("Lato-Bold", bold))
        return "Lato", "Lato-Bold"
    return "Helvetica", "Helvetica-Bold"


REGULAR_FONT, BOLD_FONT = _register_fonts()


class _InvariantCanvas(canvas.Canvas):  # type: ignore[misc]
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["invariant"] = 1
        kwargs["pageCompression"] = 1
        super().__init__(*args, **kwargs)


def build_audit_report_csv(payload: dict[str, object], report_sha256: str) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    columns = [
        "report_sha256", "result_id", "activity_id", "activity_date",
        "description", "scope", "scope_2_method", "scope_3_category",
        "activity_value", "activity_unit", "factor_id", "factor_value",
        "factor_unit", "gross_kg_co2e", "allocated_kg_co2e",
        "allocation_percentage", "formula", "methodology_version",
        "evidence_reference", "warnings", "comparison_status",
        "reporting_basis", "dcarbn_kg_co2e", "dcarbn_methodology_version",
        "uk_government_kg_co2e", "uk_government_methodology_version",
        "absolute_delta_kg_co2e", "percentage_delta",
        "comparison_unavailable_reason", "comparison_disclosure",
    ]
    writer.writerow(columns)
    comparisons = {
        str(_mapping(item.get("dcarbn_result")).get("result_id", "")): item
        for item in _mappings(payload.get("calculation_comparisons"))
    }
    for row in sorted(_mappings(payload.get("results")), key=lambda item: str(item.get("id", ""))):
        comparison = _mapping(comparisons.get(str(row.get("id", ""))))
        dcarbn = _mapping(comparison.get("dcarbn_result"))
        government = _mapping(comparison.get("uk_government_comparator"))
        writer.writerow([
            report_sha256, row.get("id"), row.get("activity_id"), row.get("activity_date"),
            row.get("description"), row.get("scope"), row.get("scope_2_method"),
            row.get("scope_3_category"), row.get("original_activity_value"),
            row.get("original_activity_unit"), row.get("selected_factor_id"),
            row.get("factor_value"), row.get("factor_activity_unit"),
            row.get("gross_kg_co2e"), row.get("allocated_kg_co2e"),
            row.get("allocation_percentage"), row.get("calculation_formula"),
            row.get("methodology_version"), row.get("evidence_reference"),
            " | ".join(str(item) for item in _sequence(row.get("warnings"))),
            comparison.get("status"), comparison.get("reporting_basis"),
            dcarbn.get("allocated_kg_co2e"), dcarbn.get("methodology_version"),
            government.get("allocated_kg_co2e"),
            government.get("methodology_version"),
            comparison.get("absolute_delta_kg_co2e"),
            comparison.get("percentage_delta"),
            comparison.get("comparison_unavailable_reason"),
            comparison.get("disclosure"),
        ])
    return output.getvalue().encode("utf-8-sig")


def build_audit_report_pdf(payload: dict[str, object], report_sha256: str) -> bytes:
    output = io.BytesIO()
    width, height = A4
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=25 * mm,
        bottomMargin=16 * mm,
        title="DcarbN Analytics GHG Inventory Report",
        author="DcarbN Analytics",
        subject="Assurance-ready greenhouse gas inventory report",
    )
    styles = _styles()
    story: list[object] = []

    inventory = _mapping(payload.get("inventory"))
    period = _mapping(payload.get("reporting_period"))
    totals = _mapping(payload.get("totals"))
    defence = _mapping(payload.get("defensibility_statement"))
    quality = _mapping(payload.get("data_quality"))
    uncertainty = _mapping(payload.get("uncertainty"))

    story.extend([
        Paragraph(escape(str(inventory.get("name", "Corporate GHG Inventory"))), styles["title"]),
        Paragraph(
            f"Reporting period: {escape(str(period.get('start_date', '')))} to "
            f"{escape(str(period.get('end_date', '')))}",
            styles["meta"],
        ),
        Paragraph(
            "Assurance-ready reporting pack. Independent verification requires a separate assurance opinion.",
            styles["intro"],
        ),
        Spacer(1, 3 * mm),
        _section("Reported emissions", styles),
        _field_table([
            ("Scope 1", _amount(totals.get("scope_1_kg_co2e"), "kg CO2e")),
            ("Scope 2 - location-based", _amount(totals.get("scope_2_location_based_kg_co2e"), "kg CO2e")),
            ("Scope 2 - market-based", _amount(totals.get("scope_2_market_based_kg_co2e"), "kg CO2e")),
            ("Scope 3", _amount(totals.get("scope_3_kg_co2e"), "kg CO2e")),
            ("Scope 2 headline basis", totals.get("scope_2_headline_basis")),
            ("Headline total", _amount(totals.get("total_t_co2e"), "t CO2e")),
        ], styles),
        _section("Defensibility statement", styles),
        Paragraph(escape(str(defence.get("preparation_basis", "Not reported"))), styles["body"]),
        Spacer(1, 1.5 * mm),
        Paragraph(escape(str(defence.get("assurance_limitation", "Not reported"))), styles["body"]),
        Spacer(1, 2 * mm),
        _field_table([
            ("Report schema", payload.get("report_schema_version")),
            ("Immutable report hash", report_sha256),
        ], styles),
    ])

    boundary = _mapping(payload.get("organisational_boundary"))
    approval = _mapping(payload.get("approval"))
    story.extend([
        _section("Boundary and governance", styles),
        _field_table([
            ("Consolidation approach", boundary.get("consolidation_approach")),
            ("Boundary status", boundary.get("status")),
            ("Approval reviewer", approval.get("reviewer_id")),
            ("Approval date", approval.get("decided_at")),
        ], styles),
        _section("Data quality and evidence", styles),
        _field_table([
            ("Activities", quality.get("activity_count")),
            ("Average quality score", quality.get("average_score")),
            ("Evidence coverage", _amount(quality.get("evidence_coverage_percent"), "%")),
            ("Quality distribution", _quality_distribution(quality.get("level_distribution"))),
        ], styles),
        _section("Uncertainty disclosure", styles),
        _field_table([
            ("Quantitative status", uncertainty.get("quantitative_status")),
            ("Confidence interval", uncertainty.get("confidence_interval")),
        ], styles),
    ])
    for source in _sequence(uncertainty.get("qualitative_sources")):
        story.append(Paragraph(f"• {escape(str(source))}", styles["bullet"]))
    story.append(Spacer(1, 2 * mm))

    dispositions = sorted(
        _mappings(payload.get("scope_3_category_dispositions")),
        key=lambda item: int(item.get("category", 0)),
    )
    scope3_rows: list[list[object]] = [[Paragraph("Scope 3 inclusions and exclusions", styles["section_text"])]]
    for item in dispositions:
        category = escape(str(item.get("category", "")))
        disposition = escape(str(item.get("disposition", "Not reported"))).title()
        rationale = escape(str(item.get("rationale", "Not reported")))
        scope3_rows.append([
            Paragraph(f"<b>Category {category}: {disposition}</b><br/>{rationale}", styles["table_body"])
        ])
    story.append(_repeatable_section_table(scope3_rows, doc.width))
    story.append(Spacer(1, 3 * mm))

    comparisons = sorted(
        _mappings(payload.get("calculation_comparisons")),
        key=lambda item: str(item.get("comparison_group_key", "")),
    )
    if comparisons:
        story.extend([
            _section("DcarbN and UK Government comparison", styles),
            Paragraph(
                "UK Government values are disclosure-only comparators and are "
                "excluded from inventory totals. Their presentation does not imply "
                "UK Government endorsement of the DcarbN methodology.",
                styles["body"],
            ),
            Spacer(1, 2 * mm),
        ])
        for comparison in comparisons:
            dcarbn = _mapping(comparison.get("dcarbn_result"))
            government = _mapping(
                comparison.get("uk_government_comparator")
            )
            story.append(_field_table([
                ("Comparison key", comparison.get("comparison_group_key")),
                ("Status", comparison.get("status")),
                ("Headline basis", comparison.get("reporting_basis")),
                ("Basis reason", comparison.get("basis_reason")),
                (
                    "DcarbN operational result",
                    _amount(dcarbn.get("allocated_kg_co2e"), "kg CO2e"),
                ),
                (
                    "DcarbN methodology",
                    dcarbn.get("methodology_version"),
                ),
                (
                    "UK Government comparator",
                    _amount(
                        government.get("allocated_kg_co2e"),
                        "kg CO2e",
                    ),
                ),
                (
                    "UK Government methodology",
                    government.get("methodology_version"),
                ),
                (
                    "Absolute difference",
                    _amount(
                        comparison.get("absolute_delta_kg_co2e"),
                        "kg CO2e",
                    ),
                ),
                (
                    "Percentage difference",
                    _amount(comparison.get("percentage_delta"), "%"),
                ),
                (
                    "Unavailable reason",
                    comparison.get("comparison_unavailable_reason"),
                ),
            ], styles))
            story.append(Spacer(1, 2 * mm))

    lineage_rows: list[list[object]] = [[Paragraph("Calculation lineage", styles["section_text"])]]
    for result in sorted(_mappings(payload.get("results")), key=lambda item: str(item.get("id", ""))):
        title = (
            f"{escape(str(result.get('scope', ''))).replace('_', ' ').title()} | "
            f"{escape(str(result.get('description', 'Not reported')))} | "
            f"{_amount(result.get('allocated_kg_co2e'), 'kg CO2e')}"
        )
        detail = (
            f"Activity: {escape(str(result.get('original_activity_value', '')))} "
            f"{escape(str(result.get('original_activity_unit', '')))} | "
            f"Factor: {escape(str(result.get('factor_value', '')))} | "
            f"Formula: {escape(str(result.get('calculation_formula', '')))}<br/>"
            f"Factor ID: {escape(str(result.get('selected_factor_id', '')))} | "
            f"Methodology: {escape(str(result.get('methodology_version', '')))} | "
            f"Evidence: {escape(str(result.get('evidence_reference', 'Not reported')))}"
        )
        lineage_rows.append([[
            Paragraph(f"<b>{title}</b>", styles["table_body"]),
            Spacer(1, 1 * mm),
            Paragraph(detail, styles["table_body"]),
        ]])
    story.append(_repeatable_section_table(lineage_rows, doc.width))

    def decorate(pdf: canvas.Canvas, _: object) -> None:
        pdf.saveState()
        pdf.setTitle("DcarbN Analytics GHG Inventory Report")
        pdf.setAuthor("DcarbN Analytics")
        pdf.setSubject("Assurance-ready greenhouse gas inventory report")
        pdf.setFillColor(NAVY)
        pdf.rect(0, height - 18 * mm, width, 18 * mm, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont(BOLD_FONT, 14)
        pdf.drawString(18 * mm, height - 11.5 * mm, "DcarbN Analytics")
        pdf.setFont(REGULAR_FONT, 7.5)
        pdf.drawRightString(width - 18 * mm, height - 11.5 * mm, "GHG Inventory Report")
        pdf.setFillColor(GREY)
        pdf.setFont(REGULAR_FONT, 6.5)
        pdf.drawString(18 * mm, 8 * mm, f"SHA-256: {report_sha256}")
        pdf.drawRightString(width - 18 * mm, 8 * mm, f"Page {pdf.getPageNumber()}")
        pdf.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate, canvasmaker=_InvariantCanvas)
    return output.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName=BOLD_FONT, fontSize=20, leading=24, textColor=NAVY, alignment=TA_LEFT, spaceAfter=5),
        "meta": ParagraphStyle("Meta", parent=base["Normal"], fontName=REGULAR_FONT, fontSize=8.5, leading=11, textColor=GREY),
        "intro": ParagraphStyle("Intro", parent=base["Normal"], fontName=REGULAR_FONT, fontSize=9, leading=12, textColor=NAVY, spaceBefore=5),
        "section_text": ParagraphStyle("SectionText", parent=base["Normal"], fontName=BOLD_FONT, fontSize=10, leading=12, textColor=colors.white),
        "body": ParagraphStyle("Body", parent=base["Normal"], fontName=REGULAR_FONT, fontSize=8.5, leading=12, textColor=NAVY),
        "bullet": ParagraphStyle("Bullet", parent=base["Normal"], fontName=REGULAR_FONT, fontSize=8.2, leading=11, textColor=NAVY, leftIndent=4 * mm, firstLineIndent=-3 * mm, spaceAfter=2),
        "label": ParagraphStyle("Label", parent=base["Normal"], fontName=BOLD_FONT, fontSize=7.8, leading=10, textColor=GREY),
        "value": ParagraphStyle("Value", parent=base["Normal"], fontName=REGULAR_FONT, fontSize=8.2, leading=10, textColor=NAVY),
        "table_body": ParagraphStyle("TableBody", parent=base["Normal"], fontName=REGULAR_FONT, fontSize=8.2, leading=11, textColor=NAVY),
    }


def _section(title: str, styles: Mapping[str, ParagraphStyle]) -> Table:
    table = Table([[Paragraph(escape(title), styles["section_text"])]], colWidths=[None])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("SPACEBEFORE", (0, 0), (-1, -1), 8),
        ("SPACEAFTER", (0, 0), (-1, -1), 5),
    ]))
    return table


def _field_table(rows: Sequence[tuple[str, object]], styles: Mapping[str, ParagraphStyle]) -> Table:
    data = [[
        Paragraph(escape(label), styles["label"]),
        Paragraph(escape(_display(value)), styles["value"]),
    ] for label, value in rows]
    table = Table(data, colWidths=[58 * mm, 116 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, LIGHT_GREY),
    ]))
    return table


def _repeatable_section_table(rows: list[list[object]], width: float) -> Table:
    table = Table(rows, colWidths=[width], repeatRows=1, splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("LEFTPADDING", (0, 0), (-1, 0), 8),
        ("RIGHTPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("LEFTPADDING", (0, 1), (-1, -1), 8),
        ("RIGHTPADDING", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, HexColor("#D8E1E5")),
    ]))
    return table


def _display(value: object) -> str:
    return "Not reported" if value in (None, "") else str(value)


def _amount(value: object, unit: str) -> str:
    return f"{_display(value)} {unit}" if value not in (None, "") else "Not reported"


def _quality_distribution(value: object) -> str:
    distribution = _mapping(value)
    return ", ".join(f"{key}={distribution.get(key, 0)}" for key in ("primary", "secondary", "estimated", "unknown"))


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []


def _mappings(value: object) -> list[Mapping[str, Any]]:
    return [item for item in _sequence(value) if isinstance(item, Mapping)]
