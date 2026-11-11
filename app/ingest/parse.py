"""PDF -> ordered elements (headings, text lines, tables) with page numbers.

Only PDFs that carry a 'Document No.' header block are treated as SOPs. This is how
Sample_Questions.pdf (which sits in the same folder) is kept out of the index.
"""
import re
from pathlib import Path

import fitz  # PyMuPDF

FOOTER_RE = re.compile(r"Uncontrolled copy when printed|^Page \d+$", re.I)
NUMBERED_RE = re.compile(r"^\d+\.\s")
BULLET_RE = re.compile(r"^[^\x00-\x7f]\s+")  # a non-ASCII bullet glyph at line start

HEADING_MIN_SIZE = 11.5
TITLE_MIN_SIZE = 14.0
WRAP_GAP = 15.5  # a line closer than this to the previous one (pt) is a wrapped continuation


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(" ", " ")).strip()


def _table_to_rows(table) -> list[list[str]]:
    rows = []
    for row in table.extract():
        cells = [_clean(c or "") for c in row]
        if any(cells):
            rows.append(cells)
    return rows


def _inside(bbox, tables) -> bool:
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return any(t.bbox[0] <= cx <= t.bbox[2] and t.bbox[1] <= cy <= t.bbox[3] for t in tables)


def parse_pdf(path: Path) -> dict | None:
    doc = fitz.open(path)
    first = doc[0].get_text()
    m_no = re.search(r"Document No\.\s*([A-Z0-9][A-Z0-9\-]+)", first)
    if not m_no:
        return None  # not an SOP (e.g. the sample-questions sheet)
    m_rev = re.search(r"Revision\s*(\d+)", first)
    m_date = re.search(r"Effective Date\s*(\d{2}-[A-Za-z]{3}-\d{4})", first)
    if not (m_rev and m_date):
        raise ValueError(f"{path.name}: found a Document No. but no revision / effective date")

    title = ""
    elements: list[dict] = []
    for pno, page in enumerate(doc, start=1):
        tables = [t for t in page.find_tables().tables]
        # The metadata block at the top ("Document No. | Revision | ...") is not content.
        content_tables = [t for t in tables if "Document No." not in " ".join(c or "" for r in t.extract() for c in r)]
        items = []  # (y, kind, payload)
        for t in content_tables:
            rows = _table_to_rows(t)
            if rows:
                items.append((t.bbox[1], "table", rows))
        prev_y, prev_size = None, None
        raw_lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = line["spans"]
                text = _clean("".join(s["text"] for s in spans))
                if not text or FOOTER_RE.search(text):
                    continue
                if _inside(line["bbox"], tables):
                    continue
                raw_lines.append((line["bbox"][1], spans[0]["size"], bool(spans[0]["flags"] & 16), text))
        raw_lines.sort(key=lambda r: r[0])
        for y, size, bold, text in raw_lines:
            if size >= TITLE_MIN_SIZE:
                title = title or text
                continue
            if "Kaveri Precision" in text:
                continue
            if bold and size >= HEADING_MIN_SIZE:
                # heading that wraps onto a second line (e.g. section 6 of Rev 04)
                if items and items[-1][1] == "heading" and not NUMBERED_RE.match(text) and y - prev_y < WRAP_GAP + 6:
                    items[-1] = (items[-1][0], "heading", items[-1][2] + " " + text)
                else:
                    items.append((y, "heading", text))
            else:
                text = BULLET_RE.sub("- ", text)
                is_new = NUMBERED_RE.match(text) or text.startswith("- ")
                is_wrap = (
                    items and items[-1][1] == "text" and prev_y is not None
                    and y - prev_y < WRAP_GAP and abs(size - prev_size) < 0.5 and not is_new
                )
                if is_wrap:
                    items[-1] = (items[-1][0], "text", items[-1][2] + " " + text)
                else:
                    items.append((y, "text", text))
            prev_y, prev_size = y, size
        items.sort(key=lambda i: i[0])
        for _, kind, payload in items:
            elements.append({"kind": kind, "page": pno, "data": payload})

    return {
        "file": path.name,
        "doc_no": m_no.group(1),
        "revision": m_rev.group(1),
        "effective_date": m_date.group(1),
        "title": title,
        "pages": len(doc),
        "elements": elements,
    }
