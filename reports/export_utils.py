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


def build_pdf_bytes(title, filter_details, headers, rows, column_widths=None):
    buffer = BytesIO()
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
    company_style = ParagraphStyle(
        "ReportCompany",
        parent=styles["Heading1"],
        fontSize=16,
        leading=19,
        textColor=REPORT_GREEN,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#102a43"),
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#52606d"),
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
        textColor=colors.HexColor("#243b53"),
    )

    elements = []
    logo_path = get_logo_path()
    heading_blocks = [
        Paragraph(COMPANY_NAME, company_style),
        Paragraph(title, title_style),
        Paragraph(_format_filter_summary(filter_details), meta_style),
        Paragraph(
            f"Generated: {timezone.localtime(timezone.now()).strftime('%B %d, %Y %I:%M %p')}",
            meta_style,
        ),
    ]

    if logo_path:
        logo_img = Image(str(logo_path), width=0.85 * inch, height=0.85 * inch)
        header = Table(
            [[logo_img, Table([[item] for item in heading_blocks], colWidths=[doc.width - 1.05 * inch])]],
            colWidths=[1.0 * inch, doc.width - 1.0 * inch],
        )
        header.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )
        elements.append(header)
    else:
        elements.extend(heading_blocks)

    elements.append(Spacer(1, 0.22 * inch))

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
        ("BACKGROUND", (0, 0), (-1, 0), REPORT_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd2d9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
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


def build_xlsx_bytes(title, filter_details, headers, rows, column_widths=None, sheet_name="Report"):
    buffer = BytesIO()
    logo_path = get_logo_path()
    logo_bytes = logo_path.read_bytes() if logo_path else None
    last_column_letter = _column_letter(max(len(headers), 3))
    filter_summary = _format_filter_summary(filter_details)

    worksheet_rows = [
        (1, [("C", 1, COMPANY_NAME)]),
        (2, [("C", 2, title)]),
        (3, [("C", 3, f"Generated: {timezone.localtime(timezone.now()).strftime('%B %d, %Y %I:%M %p')}")]),
        (4, [("C", 3, filter_summary)]),
        (6, [(_column_letter(index + 1), 4, header) for index, header in enumerate(headers)]),
    ]

    current_row = 7
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
        worksheet_rows.append((7, [("A", 5, "No records matched the selected filters.")]))

    merges = [f"C1:{last_column_letter}1", f"C2:{last_column_letter}2", f"C3:{last_column_letter}3", f"C4:{last_column_letter}4"]
    if not rows:
        merges.append(f"A7:{last_column_letter}7")

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(include_logo=bool(logo_bytes)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("docProps/app.xml", _app_xml())
        archive.writestr("docProps/core.xml", _core_xml(title))
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            _worksheet_xml(
                worksheet_rows=worksheet_rows,
                merges=merges,
                headers=headers,
                column_widths=column_widths,
                include_logo=bool(logo_bytes),
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


def _worksheet_xml(worksheet_rows, merges, headers, column_widths=None, include_logo=False):
    row_xml = []
    for row_index, cells in worksheet_rows:
        height_attrs = ' ht="22" customHeight="1"' if row_index in {1, 2, 3, 4, 6} else ""
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
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="6" topLeftCell="A7" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        f'<cols>{"".join(cols)}</cols>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        f"{merge_xml}"
        f"{drawing_xml}"
        "</worksheet>"
    )


def _styles_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="6">'
        '<font><sz val="11"/><color rgb="FF243B53"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="15"/><color rgb="FF019D66"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="13"/><color rgb="FF102A43"/><name val="Calibri"/><family val="2"/></font>'
        '<font><sz val="10"/><color rgb="FF52606D"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/></font>'
        '<font><sz val="10"/><color rgb="FF243B53"/><name val="Calibri"/><family val="2"/></font>'
        "</fonts>"
        '<fills count="4">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF019D66"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF7FAFC"/><bgColor indexed="64"/></patternFill></fill>'
        "</fills>"
        '<borders count="2">'
        '<border><left/><right/><top/><bottom/><diagonal/></border>'
        '<border><left style="thin"><color rgb="FFD9E2EC"/></left><right style="thin"><color rgb="FFD9E2EC"/></right><top style="thin"><color rgb="FFD9E2EC"/></top><bottom style="thin"><color rgb="FFD9E2EC"/></bottom><diagonal/></border>'
        "</borders>"
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="6">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="4" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="5" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="top" wrapText="1"/></xf>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


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
