from pathlib import Path
import re
import tempfile
import warnings

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image


DOCS = Path(__file__).resolve().parent
SOURCE = DOCS / "THINKBOARD_PROJECT_GUIDE.md"
OUTPUT = DOCS / "THINKBOARD_PROJECT_GUIDE.docx"
IMAGE = DOCS / "assets" / "thinkboard-system-context.png"
GREEN = "24614E"
INK = "1F2933"
MUTED = "58666F"
PALE = "EDF5F1"
PALE_BLUE = "EFF4FA"
GRID = "D8E1E4"
WHITE = "FFFFFF"
BACKTICK = chr(96)


def set_cell_fill(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), color)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color=GRID, size="5"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def set_run_font(run, name="Arial", size=9.5, color=INK, bold=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    rel_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "2463A6")
    props.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    props.append(underline)
    run.append(props)
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.append(text_node)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_inline(paragraph, text, table_cell=False):
    pattern = re.compile(
        r"(\*\*.*?\*\*|" + re.escape(BACKTICK) + r"[^" + re.escape(BACKTICK) + r"]+" +
        re.escape(BACKTICK) + r"|\[[^\]]+\]\([^)]+\))"
    )
    cursor = 0
    for match in pattern.finditer(text):
        if match.start() > cursor:
            run = paragraph.add_run(text[cursor:match.start()])
            set_run_font(run, size=8.1 if table_cell else 9.5)
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, size=8.1 if table_cell else 9.5, bold=True)
        elif token.startswith(BACKTICK):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, name="Consolas", size=7.8 if table_cell else 9.0, color="334155")
        else:
            label, target = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token).groups()
            if target.startswith("http://") or target.startswith("https://"):
                add_hyperlink(paragraph, label, target)
            else:
                run = paragraph.add_run(label)
                set_run_font(run, size=8.1 if table_cell else 9.5, color="2463A6")
        cursor = match.end()
    if cursor < len(text):
        run = paragraph.add_run(text[cursor:])
        set_run_font(run, size=8.1 if table_cell else 9.5)


def add_paragraph(doc, text, style=None, quote=False):
    paragraph = doc.add_paragraph(style=style)
    paragraph.paragraph_format.keep_together = True
    paragraph.paragraph_format.space_after = Pt(6)
    if quote:
        paragraph.paragraph_format.left_indent = Inches(0.22)
        paragraph.paragraph_format.right_indent = Inches(0.12)
        paragraph.paragraph_format.space_before = Pt(3)
        paragraph.paragraph_format.space_after = Pt(8)
        p_pr = paragraph._p.get_or_add_pPr()
        p_bdr = OxmlElement("w:pBdr")
        left = OxmlElement("w:left")
        left.set(qn("w:val"), "single")
        left.set(qn("w:sz"), "20")
        left.set(qn("w:space"), "8")
        left.set(qn("w:color"), GREEN)
        p_bdr.append(left)
        p_pr.append(p_bdr)
    add_inline(paragraph, text)
    return paragraph


def split_table_row(line):
    return [part.strip() for part in line.strip().strip("|").split("|")]


def add_markdown_table(doc, rows):
    parsed = [split_table_row(row) for row in rows]
    if len(parsed) > 1 and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in parsed[1]):
        parsed.pop(1)
    columns = max(len(row) for row in parsed)
    table = doc.add_table(rows=len(parsed), cols=columns)
    table.autofit = True
    table.alignment = 0
    set_table_borders(table)
    for r_index, row_data in enumerate(parsed):
        row = table.rows[r_index]
        prevent_row_split(row)
        if r_index == 0:
            set_repeat_table_header(row)
        for c_index in range(columns):
            cell = row.cells[c_index]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            value = row_data[c_index] if c_index < len(row_data) else ""
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            add_inline(para, value, table_cell=True)
            for run in para.runs:
                if r_index == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor.from_string(WHITE)
            if r_index == 0:
                set_cell_fill(cell, GREEN)
            elif r_index % 2 == 0:
                set_cell_fill(cell, "F5F8F7")
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_flow_table(doc):
    rows = [
        ("BROWSER AND UI", "Browser → React pages → UI components"),
        ("API REQUEST", "Pages → Axios client → Express server"),
        ("NOTES DATA", "Middleware → Notes routes → Controllers → Mongoose Note model → MongoDB"),
        ("RATE LIMIT", "Rate-limit middleware → Upstash Ratelimit → Upstash Redis counters"),
        ("CONFIGURATION", "MONGO_URI configures MongoDB; UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN configure Upstash"),
    ]
    table = doc.add_table(rows=0, cols=2)
    table.autofit = True
    set_table_borders(table)
    for index, (label, value) in enumerate(rows):
        cells = table.add_row().cells
        prevent_row_split(table.rows[-1])
        set_cell_margins(cells[0], top=110, bottom=110)
        set_cell_margins(cells[1], top=110, bottom=110)
        set_cell_fill(cells[0], GREEN)
        set_cell_fill(cells[1], PALE if index % 2 == 0 else PALE_BLUE)
        p0 = cells[0].paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        run = p0.add_run(label)
        set_run_font(run, size=8.0, color=WHITE, bold=True)
        p1 = cells[1].paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        add_inline(p1, value, table_cell=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_picture(doc, caption):
    warnings.simplefilter("ignore", Image.DecompressionBombWarning)
    with Image.open(IMAGE) as original:
        original.thumbnail((3400, 3800), Image.Resampling.LANCZOS)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            temp_path = Path(temp.name)
        original.save(temp_path, format="PNG", optimize=True)
    try:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(3)
        p.add_run().add_picture(str(temp_path), width=Inches(7.15))
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_after = Pt(8)
        run = cp.add_run(caption)
        set_run_font(run, size=8, color=MUTED, italic=True)
    finally:
        temp_path.unlink(missing_ok=True)


def add_footer(section):
    footer = section.footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.space_before = Pt(4)
    run = paragraph.add_run("ThinkBoard Project Guide   •   ")
    set_run_font(run, size=8, color=MUTED)
    field_run = OxmlElement("w:r")
    field_run.append(OxmlElement("w:rPr"))
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end_run = OxmlElement("w:r")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    field_run.append(begin)
    field_run.append(instr)
    field_run.append(separate)
    field_run.append(text)
    end_run.append(end)
    paragraph._p.append(field_run)
    paragraph._p.append(end_run)


def configure_document(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)
    add_footer(section)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.space_after = Pt(6)

    title = doc.styles["Title"]
    title.font.name = "Arial"
    title._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    title._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    title.font.size = Pt(26)
    title.font.bold = True
    title.font.color.rgb = RGBColor.from_string(INK)
    title.paragraph_format.space_after = Pt(4)

    for name, size, color in (
        ("Heading 1", 16, GREEN),
        ("Heading 2", 12.5, INK),
        ("Heading 3", 10.5, GREEN),
    ):
        style = doc.styles[name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(11 if name == "Heading 1" else 7)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.keep_with_next = True


def add_title(doc):
    title = doc.add_paragraph(style="Title")
    title.paragraph_format.space_before = Pt(4)
    run = title.add_run("ThinkBoard Project Guide")
    set_run_font(run, size=26, color=INK, bold=True)
    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(12)
    run = subtitle.add_run("Architecture, implementation, dependencies, and interview practice")
    set_run_font(run, size=12, color=GREEN)
    callout = doc.add_table(rows=1, cols=1)
    set_table_borders(callout, color="D7E7DF", size="8")
    cell = callout.cell(0, 0)
    set_cell_fill(cell, PALE)
    set_cell_margins(cell, top=145, start=170, bottom=145, end=170)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    add_inline(
        p,
        "A verified walkthrough of the current MERN notes app. It separates repository facts from unknown project history and points out where the supplied diagram differs from the code.",
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def build():
    doc = Document()
    configure_document(doc)
    doc.core_properties.title = "ThinkBoard Project Guide"
    doc.core_properties.subject = "Architecture, implementation, dependencies, and interview practice"
    add_title(doc)

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    index = 0
    if lines and lines[0].startswith("# "):
        index = 1
    paragraph_lines = []
    quote_lines = []

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(part.strip() for part in paragraph_lines)
            add_paragraph(doc, text)
            paragraph_lines = []

    def flush_quote():
        nonlocal quote_lines
        if quote_lines:
            text = " ".join(part.strip()[2:] if part.strip().startswith("> ") else part.strip() for part in quote_lines)
            add_paragraph(doc, text, quote=True)
            quote_lines = []

    while index < len(lines):
        raw = lines[index]
        line = raw.strip()
        if not line:
            flush_paragraph()
            flush_quote()
            index += 1
            continue
        if line.startswith(BACKTICK * 3 + "mermaid"):
            flush_paragraph()
            flush_quote()
            while index < len(lines) and not lines[index].strip().startswith(BACKTICK * 3):
                index += 1
            if index < len(lines):
                index += 1
            add_flow_table(doc)
            continue
        if line.startswith("![") and "](" in line:
            flush_paragraph()
            flush_quote()
            match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if match:
                add_picture(doc, match.group(1))
            index += 1
            continue
        if line.startswith("#"):
            flush_paragraph()
            flush_quote()
            level = len(line) - len(line.lstrip("#"))
            heading_text = line[level:].strip()
            paragraph = doc.add_paragraph(style=f"Heading {min(level, 3)}")
            if heading_text == "3. Architecture diagram and how the components link":
                paragraph.paragraph_format.page_break_before = True
            add_inline(paragraph, heading_text)
            index += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            flush_quote()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            add_markdown_table(doc, table_lines)
            continue
        if line.startswith("- "):
            flush_paragraph()
            flush_quote()
            paragraph = doc.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.space_after = Pt(3)
            add_inline(paragraph, line[2:])
            index += 1
            continue
        if re.match(r"^\d+\.\s+", line):
            flush_paragraph()
            flush_quote()
            paragraph = doc.add_paragraph(style="List Number")
            paragraph.paragraph_format.space_after = Pt(3)
            add_inline(paragraph, re.sub(r"^\d+\.\s+", "", line))
            index += 1
            continue
        if line.startswith(">"):
            flush_paragraph()
            quote_lines.append(line)
            index += 1
            continue
        flush_quote()
        paragraph_lines.append(line)
        index += 1

    flush_paragraph()
    flush_quote()
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
