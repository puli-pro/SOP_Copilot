"""Structure-aware chunking: one chunk per numbered section, tables kept whole.

Also contains the fixed-size baseline used by eval/run_eval.py to justify the choice.
"""
import re

SAFETY_RE = re.compile(
    r"lockout|tagout|loto|isolat|stored energy|zero energy|energi[sz]ed|re-energi[sz]e|hazard|danger|"
    r"hydraulic circuit|release[sd]? .*pressure|safety breach|their own lock|owner of the lock|lock owner|personal red lock",
    re.I,
)
HEADING_RE = re.compile(r"^(\d+)\.\s+(.*)$")
MAX_CHARS = 2600  # safety valve only; every section in the sample set is far below this


def table_lines(rows: list[list[str]]) -> list[str]:
    """Markdown lines for a table: header, separator, then one line per row (header stays attached)."""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    head, body = rows[0], rows[1:]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(r) + " |" for r in body]
    return out


def _sections(parsed: dict) -> list[dict]:
    """Group elements into sections. Tables that continue on the next page are merged."""
    sections: list[dict] = []
    cur = None
    for el in parsed["elements"]:
        if el["kind"] == "heading":
            m = HEADING_RE.match(el["data"])
            cur = {
                "number": m.group(1) if m else "",
                "title": m.group(2) if m else el["data"],
                "items": [],
                "pages": {el["page"]},
            }
            sections.append(cur)
            continue
        if cur is None:
            continue  # text before the first numbered heading is the header block
        cur["pages"].add(el["page"])
        if el["kind"] == "table":
            last = cur["items"][-1] if cur["items"] else None
            rows = el["data"]
            if last and last["kind"] == "table" and last["rows"][0] == rows[0]:
                last["rows"].extend(rows[1:])  # repeated header row on the next page: merge
                last["row_pages"].extend([el["page"]] * (len(rows) - 1))
                last["pages"].add(el["page"])
            else:
                cur["items"].append({"kind": "table", "rows": [list(r) for r in rows],
                                     "row_pages": [el["page"]] * len(rows), "pages": {el["page"]}})
        else:
            cur["items"].append({"kind": "text", "text": el["data"], "pages": {el["page"]}})
    return sections


def chunk_document(parsed: dict) -> list[dict]:
    chunks = []
    for sec in _sections(parsed):
        pieces = []  # (text, pages, [(line, page), ...])
        for it in sec["items"]:
            if it["kind"] == "table":
                lines = table_lines(it["rows"])
                lp = [it["row_pages"][0], it["row_pages"][0]] + it["row_pages"][1:]
                pieces.append(("\n".join(lines), it["pages"], list(zip(lines, lp))))
            else:
                pg = min(it["pages"])
                pieces.append((it["text"], it["pages"], [(it["text"], pg)]))
        if not pieces:
            continue
        # Split only if a section is unusually long, and never inside a piece (so never inside a table).
        groups, cur, size = [], [], 0
        for p in pieces:
            if cur and size + len(p[0]) > MAX_CHARS:
                groups.append(cur)
                cur, size = [], 0
            cur.append(p)
            size += len(p[0])
        groups.append(cur)
        for gi, g in enumerate(groups):
            body = "\n".join(p[0] for p in g)
            line_pages = [pg for p in g for (_, pg) in p[2]]
            pages = set().union(*[p[1] for p in g]) | (sec["pages"] if len(groups) == 1 else set())
            ps, pe = min(pages), max(pages)
            section_label = f"{sec['number']}. {sec['title']}" if sec["number"] else sec["title"]
            prefix = f"[{parsed['doc_no']} Rev {parsed['revision']} | {section_label} | p.{ps}" + (f"-{pe}" if pe != ps else "") + "]"
            suffix = f"-{gi + 1}" if len(groups) > 1 else ""
            chunks.append({
                "chunk_id": f"{parsed['doc_no']}-r{parsed['revision']}-s{sec['number'] or 'x'}{suffix}",
                "doc_no": parsed["doc_no"],
                "doc_title": parsed["title"],
                "revision": parsed["revision"],
                "effective_date": parsed["effective_date"],
                "file": parsed["file"],
                "section_number": sec["number"],
                "section_title": sec["title"],
                "page_start": ps,
                "page_end": pe,
                "line_pages": line_pages,
                "has_table": any("|---" in p[0] for p in g),
                "has_safety_terms": bool(SAFETY_RE.search(body)),
                "text": body,
                "text_with_prefix": prefix + "\n" + body,
            })
    return chunks


def fixed_size_chunks(parsed_pdf_text: dict[str, str], size: int = 500, overlap: int = 0) -> list[dict]:
    """Baseline for the eval: cut plain page text every `size` characters, ignoring structure."""
    out = []
    for key, meta in parsed_pdf_text.items():
        text = meta["text"]
        step = max(1, size - overlap)
        for i in range(0, len(text), step):
            piece = text[i:i + size].strip()
            if piece:
                out.append({
                    "chunk_id": f"{key}-fx{i}",
                    "doc_no": meta["doc_no"], "revision": meta["revision"], "status": meta["status"],
                    "doc_title": meta["title"], "effective_date": meta["effective_date"],
                    "file": meta["file"], "section_number": "", "section_title": "",
                    "page_start": 0, "page_end": 0, "has_table": False, "has_safety_terms": False,
                    "text": piece, "text_with_prefix": piece,
                })
    return out
