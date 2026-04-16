from __future__ import annotations

import io
from typing import Any, Dict, List


def renderer_statuses() -> Dict[str, Dict[str, Any]]:
    statuses = {
        "weasyprint": {"label": "WeasyPrint", "available": False, "detail": "HTML-to-PDF renderer with document-based styling."},
        "reportlab": {"label": "ReportLab", "available": False, "detail": "Direct PDF renderer with a structured report layout."},
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
        return render_pdf_weasyprint(html, base_url)
    if renderer == "reportlab":
        return render_pdf_reportlab(payload)
    raise ValueError(f"Unsupported renderer '{renderer}'.")


def render_pdf_weasyprint(html: str, base_url: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html, base_url=base_url).write_pdf()


def _paragraph(text: Any, style: Any) -> Any:
    from reportlab.platypus import Paragraph

    safe = str(text if text is not None else "-").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
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
    styles.add(ParagraphStyle(name="DeckEyebrow", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor(theme["accent"]), spaceAfter=5))
    styles.add(ParagraphStyle(name="DeckTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=21, leading=24, textColor=colors.HexColor(theme["ink"]), spaceAfter=10))
    styles.add(ParagraphStyle(name="DeckSubtitle", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=14, textColor=colors.HexColor(theme["muted"]), spaceAfter=8))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=13.5, leading=16, textColor=colors.HexColor(theme["ink"]), spaceAfter=8))
    styles.add(ParagraphStyle(name="MetaBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12, textColor=colors.HexColor(theme["ink"]), wordWrap="CJK"))
    styles.add(ParagraphStyle(name="TableBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, leading=10.5, textColor=colors.HexColor(theme["ink"]), wordWrap="CJK"))
    styles.add(ParagraphStyle(name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor(theme["accent"]), wordWrap="CJK"))

    story = [
        Paragraph(payload.get("report_type", "").upper() + " REPORT", styles["DeckEyebrow"]),
        Paragraph(payload.get("title", "Report"), styles["DeckTitle"]),
        Paragraph(payload.get("subtitle", ""), styles["DeckSubtitle"]),
        Paragraph(f"Generated {payload.get('generated_at', '-')} | {payload.get('source_label', 'Source')}: {payload.get('source_value', '-')}", styles["MetaBody"]),
        Spacer(1, 0.16 * inch),
    ]

    hero_cards = [["Signal", "Value", "Detail"]]
    for metric in payload.get("hero_metrics", []):
        hero_cards.append([metric.get("label", ""), metric.get("value", ""), metric.get("detail", "")])
    hero_table = Table(_table_data(["Signal", "Value", "Detail"], [{"cells": row} for row in [card for card in hero_cards[1:]]], styles["TableHead"], styles["MetaBody"]), colWidths=[1.55 * inch, 1.1 * inch, 3.55 * inch])
    hero_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme["accent_soft"])),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor(theme["line"])),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(theme["paper"]), colors.HexColor(theme["paper_alt"])]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([hero_table, Spacer(1, 0.18 * inch)])

    if payload.get("meta"):
        story.append(Paragraph("SOURCE CONTEXT", styles["DeckEyebrow"]))
        meta_rows = _table_data(["Field", "Value"], [{"cells": [item.get("label", ""), item.get("value", "")]} for item in payload.get("meta", [])], styles["TableHead"], styles["MetaBody"])
        meta_table = Table(meta_rows, colWidths=[1.7 * inch, 4.95 * inch])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme["accent_alt_soft"])),
                    ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor(theme["line"])),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(theme["paper"]), colors.HexColor(theme["paper_alt"])]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend([meta_table, Spacer(1, 0.18 * inch)])

    total_width = A4[0] - doc.leftMargin - doc.rightMargin
    for section in payload.get("sections", []):
        story.append(Paragraph(section.get("eyebrow", "").upper(), styles["DeckEyebrow"]))
        story.append(Paragraph(section.get("title", ""), styles["SectionTitle"]))
        kind = section.get("kind")
        if kind == "message":
            story.extend([Paragraph(section.get("body", ""), styles["MetaBody"]), Spacer(1, 0.14 * inch)])
            continue
        if kind == "facts":
            rows = _table_data(["Field", "Value"], [{"cells": [row.get("label", ""), row.get("value", "")]} for row in section.get("rows", [])], styles["TableHead"], styles["MetaBody"])
            table = Table(rows, colWidths=[2.1 * inch, 4.55 * inch])
        else:
            rows = section.get("rows", [])
            if not rows:
                story.extend([Paragraph(section.get("empty_message", "No rows available."), styles["MetaBody"]), Spacer(1, 0.14 * inch)])
                continue
            columns = section.get("columns", [])
            focus_index = 1 if "Raw excerpt" in columns else 2 if "Event" in columns else None
            table = Table(_table_data(columns, rows, styles["TableHead"], styles["TableBody"]), colWidths=_column_widths(len(columns), total_width, focus_index=focus_index))
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme["paper_alt"])),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(theme["line"])),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(theme["paper"]), colors.HexColor(theme["paper_alt"])]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.extend([KeepTogether(table), Spacer(1, 0.16 * inch)])

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("Anomaly Detection Workbench | ReportLab Executive PDF", styles["DeckSubtitle"]))
    doc.build(story)
    return buffer.getvalue()
