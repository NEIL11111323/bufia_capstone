from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


COMPANY_NAME = "Bayawan United Farmers Irrigation Association Incorporated"
REPORT_GREEN = colors.HexColor("#019d66")
EXPORT_THEMES = {
    "default": {
        "primary": "#019d66",
        "soft": "#dcfce7",
    },
    "rental_report": {
        "primary": "#2563eb",
        "soft": "#dbeafe",
    },
    "harvest_report": {
        "primary": "#b45309",
        "soft": "#fef3c7",
    },
    "rice_sales_report": {
        "primary": "#be123c",
        "soft": "#ffe4e6",
    },
    "financial_report": {
        "primary": "#0f766e",
        "soft": "#ccfbf1",
    },
    "machine_usage_report": {
        "primary": "#475569",
        "soft": "#e2e8f0",
    },
    "membership_report": {
        "primary": "#166534",
        "soft": "#dcfce7",
    },
}


def get_logo_path():
    candidates = []

    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root:
        candidates.append(Path(static_root) / "img" / "logo.png")

    candidates.append(Path(settings.BASE_DIR) / "static" / "img" / "logo.png")
    candidates.append(Path(settings.BASE_DIR) / "staticfiles" / "img" / "logo.png")

    for path in candidates:
        if path.exists():
            return path
    return None


def build_pdf_bytes(title, filter_details, headers, rows, column_widths=None, theme=None):
    buffer = BytesIO()
    theme_data = _resolve_export_theme(theme)
    primary_color = colors.HexColor(theme_data["primary"])
    soft_color = colors.HexColor(theme_data["soft"])
    border_color = colors.HexColor("#cbd5e1")
    body_text_color = colors.HexColor("#243b53")
    title_text_color = colors.HexColor("#1e293b")
    meta_text_color = colors.HexColor("#52606d")
    printed_at = timezone.localtime(timezone.now()).strftime("%B %d, %Y %I:%M %p")
    total_results = len(rows)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
        pageCompression=0,
    )

    styles = getSampleStyleSheet()
    eyebrow_style = ParagraphStyle(
        "ReportEyebrow",
        parent=styles["Normal"],
        fontSize=8.2,
        leading=10,
        textColor=primary_color,
        fontName="Helvetica-Bold",
        spaceAfter=2,
    )
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading2"],
        fontSize=14,
        leading=17,
        alignment=0,
        textColor=title_text_color,
        spaceAfter=1,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=9.3,
        leading=12,
        alignment=0,
        textColor=meta_text_color,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=2,
        textColor=meta_text_color,
    )
    header_style = ParagraphStyle(
        "ReportHeaderCell",
        parent=styles["Normal"],
        fontSize=8.2,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "ReportBodyCell",
        parent=styles["Normal"],
        fontSize=7.8,
        leading=10,
        textColor=body_text_color,
    )
    summary_label_style = ParagraphStyle(
        "ReportSummaryLabel",
        parent=styles["Normal"],
        fontSize=8.6,
        leading=11,
        textColor=colors.HexColor("#334155"),
        fontName="Helvetica-Bold",
    )
    summary_value_style = ParagraphStyle(
        "ReportSummaryValue",
        parent=styles["Normal"],
        fontSize=8.8,
        leading=11,
        textColor=title_text_color,
    )

    elements = []
    logo_path = get_logo_path()
    subtitle = _format_filter_summary(filter_details)
    left_heading_blocks = [
        Paragraph(COMPANY_NAME, eyebrow_style),
        Paragraph(title, title_style),
        Paragraph(subtitle, subtitle_style),
    ]
    right_heading_blocks = [
        Paragraph(f"Printed: {printed_at}", meta_style),
        Paragraph(f"Total Results: {total_results}", meta_style),
    ]

    if logo_path:
        logo_img = Image(str(logo_path), width=0.85 * inch, height=0.85 * inch)
        left_header = Table(
            [[logo_img, Table([[item] for item in left_heading_blocks], colWidths=[doc.width * 0.52 - 1.0 * inch])]],
            colWidths=[1.0 * inch, doc.width * 0.52 - 1.0 * inch],
        )
        left_header.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )
        header = Table(
            [[left_header, Table([[item] for item in right_heading_blocks], colWidths=[doc.width * 0.43])]],
            colWidths=[doc.width * 0.57, doc.width * 0.43],
        )
    else:
        header = Table(
            [
                [
                    Table([[item] for item in left_heading_blocks], colWidths=[doc.width * 0.57]),
                    Table([[item] for item in right_heading_blocks], colWidths=[doc.width * 0.43]),
                ]
            ],
            colWidths=[doc.width * 0.57, doc.width * 0.43],
        )
    header.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, border_color),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elements.append(header)

    summary_rows = []
    for left_pair, right_pair in _summary_detail_pairs(filter_details, total_results):
        summary_rows.append([
            Paragraph(escape(str(left_pair[0])), summary_label_style),
            Paragraph(escape(_display_value(left_pair[1])), summary_value_style),
            Paragraph(escape(str(right_pair[0])), summary_label_style) if right_pair else "",
            Paragraph(escape(_display_value(right_pair[1])), summary_value_style) if right_pair else "",
        ])
    if summary_rows:
        summary_table = Table(summary_rows, colWidths=[doc.width * 0.17, doc.width * 0.33, doc.width * 0.17, doc.width * 0.33])
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), soft_color),
                ("BACKGROUND", (2, 0), (2, -1), soft_color),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(Spacer(1, 0.14 * inch))
        elements.append(summary_table)

    elements.append(Spacer(1, 0.18 * inch))

    normalized_widths = _normalize_pdf_widths(column_widths, doc.width, len(headers))
    table_rows = [[Paragraph(escape(str(header)), header_style) for header in headers]]

    if rows:
        for row in rows:
            table_rows.append([Paragraph(escape(_display_value(value)), body_style) for value in row])
    else:
        empty_row = [Paragraph("No records matched the selected filters.", body_style)] + [""] * (len(headers) - 1)
        table_rows.append(empty_row)

    table = Table(table_rows, colWidths=normalized_widths, repeatRows=1)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, border_color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 1), (-1, -1), 5),
        ("RIGHTPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]
    if not rows:
        table_style.append(("SPAN", (0, 1), (-1, 1)))
        table_style.append(("ALIGN", (0, 1), (-1, 1), "CENTER"))
    table.setStyle(TableStyle(table_style))
    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()


def build_xlsx_bytes(title, filter_details, headers, rows, column_widths=None, sheet_name="Report", theme=None):
    buffer = BytesIO()
    theme_data = _resolve_export_theme(theme)
    logo_path = get_logo_path()
    logo_bytes = logo_path.read_bytes() if logo_path else None
    last_column_letter = _column_letter(max(len(headers), 9))
    printed_at = timezone.localtime(timezone.now()).strftime("%B %d, %Y %I:%M %p")
    filter_summary = _format_filter_summary(filter_details)
    summary_pairs = _summary_detail_pairs(filter_details, len(rows))

    worksheet_rows = [
        (1, [("C", 1, title), ("H", 3, f"Printed: {printed_at}")]),
        (2, [("C", 2, COMPANY_NAME), ("H", 3, f"Total Results: {len(rows)}")]),
        (3, [("C", 2, filter_summary)]),
    ]

    summary_start_row = 5
    for offset, (left_pair, right_pair) in enumerate(summary_pairs):
        row_index = summary_start_row + offset
        worksheet_rows.append(
            (
                row_index,
                [
                    ("A", 6, left_pair[0]),
                    ("B", 7, left_pair[1]),
                    ("E", 6, right_pair[0] if right_pair else ""),
                    ("F", 7, right_pair[1] if right_pair else ""),
                ],
            )
        )

    header_row = summary_start_row + max(len(summary_pairs), 1) + 2
    worksheet_rows.append(
        (header_row, [(_column_letter(index + 1), 4, header) for index, header in enumerate(headers)])
    )

    current_row = header_row + 1
    if rows:
        for row in rows:
            worksheet_rows.append(
                (
                    current_row,
                    [(_column_letter(index + 1), 5, _display_value(value)) for index, value in enumerate(row)],
                )
            )
            current_row += 1
    else:
        worksheet_rows.append((current_row, [("A", 5, "No records matched the selected filters.")]))

    merges = [
        "C1:F1",
        "C2:F2",
        "C3:F3",
        "H1:I1",
        "H2:I2",
        "B5:D5",
        "F5:I5",
    ]
    if len(summary_pairs) > 1:
        merges.extend(["B6:D6", "F6:I6"])
    if len(summary_pairs) > 2:
        for offset in range(2, len(summary_pairs)):
            row_index = summary_start_row + offset
            merges.extend([f"B{row_index}:D{row_index}", f"F{row_index}:I{row_index}"])
    if not rows:
        merges.append(f"A{current_row}:{last_column_letter}{current_row}")

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(include_logo=bool(logo_bytes)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("docProps/app.xml", _app_xml())
        archive.writestr("docProps/core.xml", _core_xml(title))
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/styles.xml", _styles_xml(theme_data))
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            _worksheet_xml(
                worksheet_rows=worksheet_rows,
                merges=merges,
                headers=headers,
                column_widths=column_widths,
                include_logo=bool(logo_bytes),
                freeze_row=header_row,
            ),
        )
        if logo_bytes:
            archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", _worksheet_rels_xml())
            archive.writestr("xl/drawings/drawing1.xml", _drawing_xml())
            archive.writestr("xl/drawings/_rels/drawing1.xml.rels", _drawing_rels_xml())
            archive.writestr("xl/media/logo.png", logo_bytes)

    return buffer.getvalue()


def _display_value(value):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _format_filter_summary(filter_details):
    visible_details = [f"{label}: {value}" for label, value in filter_details if value]
    return " | ".join(visible_details) if visible_details else "Filtered Report"


def _resolve_export_theme(theme):
    if isinstance(theme, dict):
        base = dict(EXPORT_THEMES["default"])
        base.update(theme)
        return base
    if isinstance(theme, str) and theme in EXPORT_THEMES:
        return EXPORT_THEMES[theme]
    return EXPORT_THEMES["default"]


def _summary_detail_pairs(filter_details, total_results):
    visible_details = [(str(label), _display_value(value)) for label, value in filter_details if value not in (None, "")]
    if not any("total result" in label.lower() for label, _ in visible_details):
        visible_details.append(("Total Results", total_results))
    if not visible_details:
        visible_details = [("Report Scope", "Filtered Report"), ("Total Results", total_results)]
    if len(visible_details) % 2:
        visible_details.append(None)

    detail_pairs = []
    for index in range(0, len(visible_details), 2):
        left_pair = visible_details[index]
        right_pair = visible_details[index + 1]
        detail_pairs.append((left_pair, right_pair))
    return detail_pairs


def _normalize_pdf_widths(widths, total_width, count):
    if widths and len(widths) == count:
        weight_total = sum(widths) or count
        return [(total_width * width) / weight_total for width in widths]
    return [total_width / count] * count


def _column_letter(index):
    letters = []
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def _worksheet_xml(worksheet_rows, merges, headers, column_widths=None, include_logo=False, freeze_row=7):
    row_xml = []
    for row_index, cells in worksheet_rows:
        if row_index == 1:
            height_attrs = ' ht="24" customHeight="1"'
        elif row_index in {2, 3}:
            height_attrs = ' ht="20" customHeight="1"'
        elif row_index in {5, 6, freeze_row}:
            height_attrs = ' ht="22" customHeight="1"'
        else:
            height_attrs = ""
        cell_xml = []
        for column, style, value in cells:
            cell_ref = f"{column}{row_index}"
            escaped_value = escape(_display_value(value))
            cell_xml.append(
                f'<c r="{cell_ref}" t="inlineStr" s="{style}"><is><t xml:space="preserve">{escaped_value}</t></is></c>'
            )
        row_xml.append(f"<row r=\"{row_index}\"{height_attrs}>{''.join(cell_xml)}</row>")

    max_columns = max(len(headers), 6)
    cols = []
    for index in range(1, max_columns + 1):
        width = 14
        if column_widths and index <= len(column_widths):
            width = column_widths[index - 1]
        cols.append(f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>')

    merge_xml = ""
    if merges:
        merge_items = "".join(f'<mergeCell ref="{merge_ref}"/>' for merge_ref in merges)
        merge_xml = f'<mergeCells count="{len(merges)}">{merge_items}</mergeCells>'

    drawing_xml = '<drawing r:id="rId1"/>' if include_logo else ""

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{freeze_row}" topLeftCell="A{freeze_row + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        f'<cols>{"".join(cols)}</cols>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        f"{merge_xml}"
        f"{drawing_xml}"
        "</worksheet>"
    )


def _styles_xml(theme):
    primary_argb = _hex_argb(theme["primary"])
    soft_argb = _hex_argb(theme["soft"])
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="8">'
        '<font><sz val="11"/><color rgb="FF243B53"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="15"/><color rgb="FF1E293B"/><name val="Calibri"/><family val="2"/></font>'
        f'<font><sz val="10"/><color rgb="{primary_argb}"/><name val="Calibri"/><family val="2"/></font>'
        '<font><sz val="10"/><color rgb="FF52606D"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/></font>'
        '<font><sz val="10"/><color rgb="FF243B53"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="10"/><color rgb="FF334155"/><name val="Calibri"/><family val="2"/></font>'
        '<font><sz val="10"/><color rgb="FF1E293B"/><name val="Calibri"/><family val="2"/></font>'
        "</fonts>"
        '<fills count="5">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        f'<fill><patternFill patternType="solid"><fgColor rgb="{primary_argb}"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF7FAFC"/><bgColor indexed="64"/></patternFill></fill>'
        f'<fill><patternFill patternType="solid"><fgColor rgb="{soft_argb}"/><bgColor indexed="64"/></patternFill></fill>'
        "</fills>"
        '<borders count="2">'
        '<border><left/><right/><top/><bottom/><diagonal/></border>'
        '<border><left style="thin"><color rgb="FFD9E2EC"/></left><right style="thin"><color rgb="FFD9E2EC"/></right><top style="thin"><color rgb="FFD9E2EC"/></top><bottom style="thin"><color rgb="FFD9E2EC"/></bottom><diagonal/></border>'
        "</borders>"
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="8">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="4" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="5" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="top" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="6" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="7" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


def _hex_argb(value):
    normalized = str(value or "").strip().lstrip("#")
    if len(normalized) == 6:
        return f"FF{normalized.upper()}"
    if len(normalized) == 8:
        return normalized.upper()
    return "FF019D66"


def _content_types_xml(include_logo=False):
    defaults = [
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
    ]
    if include_logo:
        defaults.append('<Default Extension="png" ContentType="image/png"/>')

    overrides = [
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    if include_logo:
        overrides.append(
            '<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        f'{"".join(defaults)}{"".join(overrides)}'
        "</Types>"
    )


def _root_rels_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _app_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>BUFIA Reports</Application>"
        "</Properties>"
    )


def _core_xml(title):
    created = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_title = escape(title)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{safe_title}</dc:title>"
        "<dc:creator>BUFIA Reports</dc:creator>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _workbook_xml(sheet_name):
    safe_name = escape(sheet_name[:31] or "Report")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets>'
        f'<sheet name="{safe_name}" sheetId="1" r:id="rId1"/>'
        "</sheets>"
        "</workbook>"
    )


def _workbook_rels_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )


def _worksheet_rels_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/>'
        "</Relationships>"
    )


def _drawing_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<xdr:twoCellAnchor editAs="oneCell">'
        '<xdr:from><xdr:col>0</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>0</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
        '<xdr:to><xdr:col>1</xdr:col><xdr:colOff>304800</xdr:colOff><xdr:row>3</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>'
        '<xdr:pic>'
        '<xdr:nvPicPr>'
        '<xdr:cNvPr id="1" name="BUFIA Logo" descr="BUFIA Logo"/>'
        '<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr>'
        "</xdr:nvPicPr>"
        '<xdr:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
        '<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>'
        "</xdr:pic>"
        "<xdr:clientData/>"
        "</xdr:twoCellAnchor>"
        "</xdr:wsDr>"
    )


def _drawing_rels_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/logo.png"/>'
        "</Relationships>"
    )
