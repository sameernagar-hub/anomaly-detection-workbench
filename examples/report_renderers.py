from __future__ import annotations

import io
import re
from typing import Any, Dict, List


def renderer_statuses() -> Dict[str, Dict[str, Any]]:
    statuses = {
        "weasyprint": {"label": "Studio Canvas", "available": False, "detail": "WeasyPrint PDF layout with structured sections and full-page styling."},
        "reportlab": {"label": "Executive Brief", "available": False, "detail": "ReportLab PDF layout with compact sections and print-focused formatting."},
    }
    try:
        import weasyprint  # noqa: F401

        statuses["weasyprint"]["available"] = True
    except Exception as exc:  # pragma: no cover
        statuses["weasyprint"]["detail"] = f"Unavailable: {exc}"
    try:
        import reportlab  # noqa: F401

        statuses["reportlab"]["available"] = True
    except Exception as exc:  # pragma: no cover
        statuses["reportlab"]["detail"] = f"Unavailable: {exc}"
    return statuses


def render_pdf(payload: Dict[str, Any], renderer: str, html: str, base_url: str) -> bytes:
    if renderer == "weasyprint":
        return render_pdf_studio(payload, html=html, base_url=base_url)
    if renderer == "reportlab":
        return render_pdf_reportlab(payload)
    raise ValueError(f"Unsupported renderer '{renderer}'.")


def _wrap_long_token(token: str, width: int = 26) -> str:
    if len(token) <= width:
        return token
    return "<br/>".join(token[index:index + width] for index in range(0, len(token), width))


def _reportlab_safe_text(text: Any) -> str:
    safe = str(text if text is not None else "-")
    safe = safe.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    parts = re.split(r"(\s+)", safe)
    wrapped: List[str] = []
    for part in parts:
        if not part or part.isspace():
            wrapped.append(part)
            continue
        if len(part) > 34:
            wrapped.append(_wrap_long_token(part, width=26))
        else:
            wrapped.append(part)
    return "".join(wrapped)


def _paragraph(text: Any, style: Any) -> Any:
    from reportlab.platypus import Paragraph

    safe = _reportlab_safe_text(text)
    return Paragraph(safe, style)


def _table_data(columns: List[str], rows: List[Dict[str, Any]], header_style: Any, body_style: Any) -> List[List[Any]]:
    data: List[List[Any]] = [[_paragraph(column, header_style) for column in columns]]
    for row in rows:
        data.append([_paragraph(cell, body_style) for cell in row.get("cells", [])])
    return data


def _column_widths(count: int, total_width: float, focus_index: int | None = None) -> List[float]:
    if count <= 1:
        return [total_width]
    if focus_index is None or focus_index >= count:
        return [total_width / count] * count
    side = total_width * 0.46 / max(1, count - 1)
    widths = [side] * count
    widths[focus_index] = total_width * 0.54
    return widths


def render_pdf_studio(payload: Dict[str, Any], html: str, base_url: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html, base_url=base_url).write_pdf()


def render_pdf_reportlab(payload: Dict[str, Any]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    theme = payload.get("theme", {})
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.52 * inch, rightMargin=0.52 * inch, topMargin=0.52 * inch, bottomMargin=0.52 * inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ExecKicker", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white, alignment=1))
    styles.add(ParagraphStyle(name="ExecEyebrow", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.6, leading=9.5, textColor=colors.HexColor(theme["accent"]), spaceAfter=4))
    styles.add(ParagraphStyle(name="ExecTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=22, leading=25, textColor=colors.HexColor(theme["ink"]), spaceAfter=6))
    styles.add(ParagraphStyle(name="ExecSubtitle", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.6, leading=13.2, textColor=colors.HexColor(theme["muted"]), spaceAfter=4))
    styles.add(ParagraphStyle(name="ExecBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.8, leading=11.6, textColor=colors.HexColor(theme["ink"]), wordWrap="CJK"))
    styles.add(ParagraphStyle(name="ExecLabel", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=colors.HexColor(theme["muted"]), wordWrap="CJK"))
    styles.add(ParagraphStyle(name="ExecValue", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=16, leading=18, textColor=colors.HexColor(theme["ink"]), wordWrap="CJK"))
    styles.add(ParagraphStyle(name="ExecMetricBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=10.2, textColor=colors.HexColor(theme["muted"]), wordWrap="CJK"))
    styles.add(ParagraphStyle(name="SectionBand", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10.4, leading=12.5, textColor=colors.white))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=12.5, leading=14.8, textColor=colors.HexColor(theme["ink"]), spaceAfter=4))
    styles.add(ParagraphStyle(name="SectionSummary", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.6, leading=11, textColor=colors.HexColor(theme["muted"]), spaceAfter=4, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="TableBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.9, leading=9.8, textColor=colors.HexColor(theme["ink"]), wordWrap="CJK"))
    styles.add(ParagraphStyle(name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.8, leading=9.5, textColor=colors.HexColor(theme["accent"]), wordWrap="CJK"))

    total_width = A4[0] - doc.leftMargin - doc.rightMargin

    def decorate_page(canvas: Any, pdf_doc: Any) -> None:
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(theme["canvas"]))
        canvas.rect(0, 0, width, height, stroke=0, fill=1)

        canvas.setFillColor(colors.HexColor(theme["canvas_alt"]))
        canvas.circle(width - 0.9 * inch, height - 0.8 * inch, 0.7 * inch, stroke=0, fill=1)
        canvas.circle(0.85 * inch, 0.95 * inch, 0.55 * inch, stroke=0, fill=1)

        sheet_x = 0.28 * inch
        sheet_y = 0.28 * inch
        sheet_w = width - (0.56 * inch)
        sheet_h = height - (0.56 * inch)
        canvas.setFillColor(colors.HexColor(theme["paper"]))
        canvas.roundRect(sheet_x, sheet_y, sheet_w, sheet_h, 18, stroke=0, fill=1)

        canvas.setStrokeColor(colors.HexColor(theme["line_strong"]))
        canvas.setLineWidth(0.8)
        canvas.roundRect(sheet_x, sheet_y, sheet_w, sheet_h, 18, stroke=1, fill=0)

        canvas.setFillColor(colors.HexColor(theme["accent"]))
        canvas.rect(sheet_x + 14, height - 0.56 * inch, sheet_w - 28, 0.09 * inch, stroke=0, fill=1)

        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor(theme["muted"]))
        canvas.drawString(sheet_x + 18, sheet_y + 14, f"Anomaly Detection Workbench | {payload.get('renderer_label', 'Executive Brief')}")
        canvas.drawRightString(sheet_x + sheet_w - 18, sheet_y + 14, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    def metric_card(metric: Dict[str, Any]) -> Table:
        tone = metric.get("tone", "default")
        if tone == "accent":
            top_bg = colors.HexColor(theme["accent_alt_soft"])
        elif tone == "warn":
            top_bg = colors.HexColor(theme["accent_soft"])
        else:
            top_bg = colors.HexColor(theme["paper_alt"])

        card = Table(
            [[
                _paragraph(metric.get("label", ""), styles["ExecLabel"]),
                _paragraph(metric.get("value", ""), styles["ExecValue"]),
                _paragraph(metric.get("detail", ""), styles["ExecMetricBody"]),
            ]],
            colWidths=[total_width / 4.0 - 6],
        )
        card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), top_bg),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(theme["line"])),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        return card

    def section_shell(eyebrow: str, title: str, content: Any, summary: str = "") -> Table:
        shell = Table(
            [
                [_paragraph(eyebrow.upper(), styles["SectionBand"])],
                [_paragraph(title, styles["SectionTitle"])],
                [_paragraph(summary, styles["SectionSummary"]) if summary else Spacer(1, 0.01 * inch)],
                [content],
            ],
            colWidths=[total_width],
        )
        shell.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme["accent"])),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor(theme["paper"])),
                    ("BOX", (0, 0), (-1, -1), 0.55, colors.HexColor(theme["line"])),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.55, colors.HexColor(theme["line_strong"])),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 11),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                    ("TOPPADDING", (0, 1), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 9),
                ]
            )
        )
        return shell

    title_block = Table(
        [
            [
                Table(
                    [
                        [_paragraph(payload.get("report_type", "").upper() + " REPORT", styles["ExecEyebrow"])],
                        [_paragraph(payload.get("title", "Report"), styles["ExecTitle"])],
                        [_paragraph(payload.get("subtitle", ""), styles["ExecSubtitle"])],
                    ],
                    colWidths=[total_width * 0.72],
                ),
                Table(
                    [
                        [_paragraph("PDF EXPORT", styles["ExecKicker"])],
                        [_paragraph(payload.get("generated_at", "-"), styles["ExecBody"])],
                        [_paragraph(f"{payload.get('source_label', 'Source')}: {payload.get('source_value', '-')}", styles["ExecBody"])],
                    ],
                    colWidths=[total_width * 0.28],
                ),
            ]
        ],
        colWidths=[total_width * 0.72, total_width * 0.28],
    )
    title_block.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(theme["accent"])),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(theme["paper"])),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(theme["line_strong"])),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    story = [title_block, Spacer(1, 0.16 * inch)]

    metrics = list(payload.get("hero_metrics", []))
    if metrics:
        metric_rows = []
        row = []
        card_width = (total_width - 18) / 4.0
        for metric in metrics:
            row.append(metric_card(metric))
            if len(row) == 4:
                metric_rows.append(row)
                row = []
        if row:
            while len(row) < 4:
                row.append(Spacer(card_width, 0.01 * inch))
            metric_rows.append(row)
        metric_grid = Table(metric_rows, colWidths=[card_width] * 4, hAlign="LEFT")
        metric_grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.extend([section_shell("Summary metrics", "Current metrics", metric_grid, "A compact summary of the selected report values."), Spacer(1, 0.15 * inch)])

    if payload.get("meta"):
        meta_rows = _table_data(["Field", "Value"], [{"cells": [item.get("label", ""), item.get("value", "")]} for item in payload.get("meta", [])], styles["TableHead"], styles["ExecBody"])
        meta_table = Table(meta_rows, colWidths=[1.45 * inch, total_width - 1.45 * inch])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme["accent_alt_soft"])),
                    ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor(theme["line"])),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(theme["paper"]), colors.HexColor(theme["paper_alt"])]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.extend([section_shell("Context", "Source registry", meta_table, "Execution context, identifiers, and source metadata captured for this export."), Spacer(1, 0.15 * inch)])

    for section in payload.get("sections", []):
        kind = section.get("kind")
        if kind == "message":
            content = _paragraph(section.get("body", ""), styles["ExecBody"])
            summary = "Status message"
        elif kind == "facts":
            fact_rows = [[_paragraph(row.get("label", ""), styles["ExecLabel"]), _paragraph(row.get("value", ""), styles["ExecBody"])] for row in section.get("rows", [])]
            content = Table(fact_rows, colWidths=[1.8 * inch, total_width - 1.8 * inch])
            content.setStyle(
                TableStyle(
                    [
                        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor(theme["paper_alt"]), colors.HexColor(theme["paper"])]),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(theme["line"])),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            summary = "Structured values"
        else:
            rows = section.get("rows", [])
            if not rows:
                content = _paragraph(section.get("empty_message", "No rows available."), styles["ExecBody"])
                summary = "No tabular rows were available for this section."
            else:
                columns = section.get("columns", [])
                focus_index = 1 if "Raw excerpt" in columns else 2 if "Event" in columns else None
                content = Table(_table_data(columns, rows, styles["TableHead"], styles["TableBody"]), colWidths=_column_widths(len(columns), total_width, focus_index=focus_index))
                content.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme["paper_alt"])),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(theme["line"])),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(theme["paper"]), colors.HexColor(theme["paper_alt"])]),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                summary = f"{len(rows)} rows included in this section."

        story.extend([section_shell(section.get("eyebrow", ""), section.get("title", ""), content, summary), Spacer(1, 0.14 * inch)])

    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph("Anomaly Detection Workbench | Executive Brief PDF | Compact report layout", styles["ExecSubtitle"]))
    doc.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    return buffer.getvalue()
