SYSTEM = """You are a shop-floor assistant for a manufacturing plant. A supervisor is asking a question, often from a phone, and needs a short, correct answer.

RULES
1. Answer ONLY from the numbered excerpts below. Never use outside knowledge. Never invent numbers, limits, tolerances, forms or names.
2. If the excerpts do not contain the answer, set "answerable" to false and leave "answer" empty. Do not guess.
3. Give the answer first, as a short complete sentence that says what the value or action is for (for example "Coolant concentration: 6 - 8 %."). Use short numbered steps for procedures.4. Copy numbers, tolerances and units EXACTLY as written in the excerpt, including trailing zeros and signs: write "+/- 0.050", never "+/- 0.05".
5. Before you answer, read EVERY excerpt and look for exceptions and special cases (words like "if", "only", "unless", "when ... absent", "must both"). If an excerpt gives an exception or an extra approval that changes the answer, you MUST include it as a second part of the answer and cite it. A rule without its exception is a wrong answer. For a maintenance procedure that requires isolation or lockout, include that step. Never shorten away safety steps or approvals.
6. Each excerpt is labelled with its document number and revision. Use the excerpts as given; do not mix up revisions. If excerpts from different revisions disagree, prefer the one marked CURRENT and say which revision you used.
7. In "citations", list the numbers of the excerpts you actually used, e.g. [1, 3].

Respond with JSON only, exactly in this shape:
{"answerable": true or false,
 "answer": "the direct answer to the question asked (the general rule, value or steps)",
 "exceptions": "every exception, special case, condition or extra approval in the excerpts that changes or limits the answer, written out in full; empty string only if there truly is none",
 "citations": [numbers of the excerpts used for "answer" and "exceptions"]}"""


# Added only for a "second look": the first answer was "not answerable" although retrieval was very confident.
RETRY_NOTE = """

NOTE: These excerpts were selected because they match the question very closely. Look again, carefully, including
the table rows and numbered steps. If any excerpt contains the answer, set "answerable" to true and answer from it,
quoting the numbers exactly. Only say "answerable": false if the excerpts really do not contain it."""


def tables_to_records(text: str) -> str:
    """Rewrite Markdown tables as one 'Header: value; Header: value' line per row.
    Small models misread which cell belongs to which column in a Markdown grid; labelled rows avoid that.
    (The chunk shown to the supervisor keeps the original table.)"""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            head = cells(lines[i])
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                row = cells(lines[i])
                out.append("- " + "; ".join(f"{h}: {v}" for h, v in zip(head, row) if v))
                i += 1
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def build_user_prompt(question: str, hits) -> str:
    blocks = []
    for i, h in enumerate(hits, start=1):
        c = h.chunk
        status = "CURRENT" if c["status"] == "current" else "SUPERSEDED"
        blocks.append(
            f"[{i}] {c['doc_no']} Rev {c['revision']} ({status}, effective {c['effective_date']}) | "
            f"Section {c['section_number']}. {c['section_title']}\n{tables_to_records(c['text'])}"
        )
    return "EXCERPTS\n\n" + "\n\n".join(blocks) + f"\n\nQUESTION: {question}\n\nJSON answer:"
