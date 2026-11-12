"""The question -> answer flow: retrieve, gate, ask the LLM, validate citations, build the response."""
import json
import re
import time
import uuid
from datetime import datetime, timezone

from app import config
from app.rag import llm
from app.rag.prompts import RETRY_NOTE, SYSTEM, build_user_prompt
from app.rag.retriever import Hit, Retriever, tokenize

_retriever: Retriever | None = None

OWNER_BY_PREFIX = {
    "MNT": "the maintenance engineer",
    "QC": "the QC / Supplier Quality team",
    "SAF": "the Safety Officer",
}


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def _best_page(hit: Hit, qtokens: set[str]) -> int:
    """For a chunk that spans pages, link to the page whose lines match the question best."""
    c = hit.chunk
    pages = c.get("line_pages") or []
    if not pages or c["page_start"] == c["page_end"]:
        return c["page_start"]
    lines = c["text"].split("\n")
    codes = {t for t in qtokens if re.match(r"^[a-z]{1,4}-\d", t)}  # AL-104, BH-220, ...
    skip = set()
    for i, line in enumerate(lines):
        if line.startswith("|---"):
            skip.update({i, i - 1})  # a table's separator and header row say nothing about which row was asked for
    best, best_score = pages[0], -1
    for i, (line, pg) in enumerate(zip(lines, pages)):
        if i in skip:
            continue
        toks = set(tokenize(line))
        score = len(qtokens & toks) + 5 * len(codes & toks)  # an exact code match outweighs generic words
        if score > best_score:
            best, best_score = pg, score
    return best


def _source(n: int, hit: Hit, qtokens: set[str], cited: bool) -> dict:
    c = hit.chunk
    page = _best_page(hit, qtokens)
    return {
        "n": n,
        "doc_no": c["doc_no"],
        "title": c["doc_title"],
        "revision": c["revision"],
        "effective_date": c["effective_date"],
        "status": c["status"],
        "section": f"{c['section_number']}. {c['section_title']}".strip(". "),
        "page": page,
        "page_range": [c["page_start"], c["page_end"]],
        "text": c["text"],
        "file": c["file"],
        "pdf_url": f"/api/pdf/{c['file']}#page={page}",
        "cited": cited,
        "also": False,
        "required": False,
        "score": round(hit.rrf, 4),
    }


def _matched_row(hits: list[Hit], ns: list[int], qtokens: set[str]) -> dict | None:
    """The table row the question is about, copied from the document with its column labels. Computed by the app
    (not the model), so a lookup such as a tolerance, an alarm or a schedule is always shown exactly as written.
    A row counts if the question names its code, or shares at least two words with it and no other row does as well."""
    codes = {t for t in qtokens if re.match(r"^[a-z]{1,4}-\d", t)}
    cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
    for n in ns:
        chunk = hits[n - 1].chunk
        lines, pages = chunk["text"].split("\n"), chunk.get("line_pages") or []
        scored = []  # (score, header, row, line index)
        for i in range(len(lines) - 1):
            if not (lines[i].startswith("|") and lines[i + 1].startswith("|---")):
                continue
            head, j = cells(lines[i]), i + 2
            while j < len(lines) and lines[j].startswith("|"):
                row = cells(lines[j])
                toks = set(tokenize(" ".join(row)))
                scored.append((99 if codes & toks else len(qtokens & toks), head, row, j))
                j += 1
        if not scored:
            continue
        scored.sort(key=lambda s: -s[0])
        top = scored[0]
        unique = len(scored) == 1 or scored[1][0] < top[0] or top[0] == 99
        if top[0] >= 2 and unique:
            _, head, row, j = top
            return {
                "doc_no": chunk["doc_no"], "revision": chunk["revision"],
                "section": f"{chunk['section_number']}. {chunk['section_title']}".strip(". "),
                "page": pages[j] if j < len(pages) else chunk["page_start"],
                "fields": [[h, v] for h, v in zip(head, row) if v],
            }
    return None


def _required_evidence(hits: list[Hit], cited_ns: list[int], qtokens: set[str]) -> list[dict]:
    """Deterministic requirement: when an answer rests on a rule that has a linked exception section,
    that exception is shown verbatim next to the answer, whatever the model wrote."""
    index = {h.chunk["chunk_id"]: n for n, h in enumerate(hits, start=1)}
    out, seen = [], set()
    for c in cited_ns:
        cited_chunk = hits[c - 1].chunk
        # Works both ways: an answer on a rule requires its exceptions; an answer on an exception requires the rule.
        links = [(i, "exception") for i in cited_chunk.get("qualified_by", [])] + \
                [(i, "rule") for i in cited_chunk.get("exception_for", [])]
        if not links:
            continue
        # The pair always travels together: the partner(s) AND the cited section itself, verbatim, whichever
        # half the model happened to cite. (A section the model also cited still gets its block here.)
        members = [(index[i], kind, f"{cited_chunk['section_number']}. {cited_chunk['section_title']}")
                   for i, kind in links if i in index]
        own_kind = "exception" if cited_chunk.get("exception_for") else "rule"
        partner = next((hits[n - 1].chunk for n, _, _ in members), None)
        if partner is not None:
            members.append((c, own_kind, f"{partner['section_number']}. {partner['section_title']}"))
        for n, kind, label in members:
            if n in seen:
                continue
            seen.add(n)
            src = _source(n, hits[n - 1], qtokens, cited=False)
            out.append({
                "n": n, "kind": kind, "doc_no": src["doc_no"], "revision": src["revision"], "section": src["section"],
                "page": src["page"], "page_range": src["page_range"], "text": src["text"], "pdf_url": src["pdf_url"],
                "qualifies": label,
            })
    out.sort(key=lambda r: (r["kind"] != "rule", r["n"]))  # the rule first, then its exception
    return out


def _revision_notes(retr: Retriever, sources: list[dict]) -> list[str]:
    notes = []
    by_doc: dict[str, list[dict]] = {}
    for s in sources:
        by_doc.setdefault(s["doc_no"], []).append(s)
    for doc, srcs in by_doc.items():
        revs = sorted({c["revision"] for c in retr.chunks if c["doc_no"] == doc})
        if len(revs) < 2:
            continue
        used = sorted({s["revision"] for s in srcs})
        newest = revs[-1]
        if any(s["status"] == "superseded" for s in srcs):
            notes.append(f"{doc}: this includes superseded Rev {', '.join(r for r in used if r != newest)}. "
                         f"The current revision is Rev {newest}.")
        else:
            older = ", ".join(f"Rev {r}" for r in revs[:-1])
            notes.append(f"{doc}: answered from Rev {newest} (current). {older} is superseded and was not used.")
    return notes


def _closest(hits: list[Hit]) -> list[dict]:
    seen, out = set(), []
    for h in hits:
        c = h.chunk
        if c["doc_no"] in seen:
            continue
        seen.add(c["doc_no"])
        out.append({"doc_no": c["doc_no"], "title": c["doc_title"], "revision": c["revision"],
                    "file": c["file"], "pdf_url": f"/api/pdf/{c['file']}"})
        if len(out) == 2:
            break
    return out


def _who_to_ask(hits: list[Hit]) -> str:
    if hits:
        prefix = hits[0].chunk["doc_no"].split("-")[0]
        owner = OWNER_BY_PREFIX.get(prefix)
        if owner:
            return f"Ask {owner}, or your shift lead."
    return "Ask your shift lead or the relevant department."


_NUM_RE = re.compile(r"(?<![\d.])\d+(?:\.\d+)?(?![\d])")


def _restore_digits(answer: str, source_text: str) -> str:
    """Small models sometimes drop trailing zeros ('+/- 0.05' for '+/- 0.050'), which changes a tolerance.
    If a number in the answer is not in the source as written, but is the start of a longer number there,
    use the source's spelling."""
    source_nums = set(_NUM_RE.findall(source_text))

    def fix(m: re.Match) -> str:
        n = m.group(0)
        if n in source_nums:
            return n
        longer = [s for s in source_nums if s.startswith(n) and len(s) > len(n) and set(s[len(n):]) <= {"0"}]
        return longer[0] if len(longer) == 1 else n

    return _NUM_RE.sub(fix, answer)


def _supports(answer: str, chunk_text: str, model_cited: bool) -> bool:
    """Does this excerpt actually contain what the answer says? Compared on distinctive words and numbers."""
    words = {t for t in tokenize(answer) if len(t) >= 3 or any(ch.isdigit() for ch in t)}
    if not words:
        return False
    found = len(words & set(tokenize(chunk_text))) / len(words)
    # an excerpt the model named needs some support (answers that combine a rule and an exception draw on
    # several excerpts, so each covers only part of the text); one it did not name needs strong support
    return found >= (0.3 if model_cited else 0.6)


def _trace(record: dict) -> None:
    try:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (config.LOG_DIR / "trace.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # logging must never break an answer


def ask(question: str) -> dict:
    t0 = time.time()
    retr = get_retriever()
    question = question.strip()
    trace_id = uuid.uuid4().hex[:8]

    hits, info = retr.search(question)
    hits = retr.add_linked(hits, question, info["include_superseded"])
    hits = retr.add_exceptions(hits)  # required evidence is always in the results, and in the LLM's context
    qtokens = set(tokenize(info["normalised_query"]))

    resp: dict = {
        "trace_id": trace_id, "question": question, "answerable": False, "mode": "not_found",
        "answer": "", "safety_flag": False, "required": [], "matched_row": None, "sources": [], "closest": [],
        "revision_notes": [], "notice": "", "reason": "",
    }

    def finish() -> dict:
        resp["latency_ms"] = int((time.time() - t0) * 1000)
        _trace({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "trace_id": trace_id,
            "question": question, "normalised": info["normalised_query"],
            "include_superseded": info["include_superseded"],
            "retrieved": [{"id": h.chunk["chunk_id"], "rrf": round(h.rrf, 4), "cos": round(h.cosine, 3),
                           "bm25": round(h.bm25, 2), "overlap": h.overlap} for h in hits],
            "mode": resp["mode"], "answerable": resp["answerable"], "reason": resp["reason"],
            "citations": [s["n"] for s in resp["sources"] if s["cited"]],
            "required_evidence": [r["n"] for r in resp["required"]], "latency_ms": resp["latency_ms"],
        })
        return resp

    # Layer 0: the question names a specific code (alarm, part, form, machine) that no document contains.
    unknown = retr.unknown_codes(info["normalised_query"])
    if unknown:
        shown = ", ".join(c.upper() for c in unknown)
        resp.update(reason=f"unknown code: {shown} does not appear in any document",
                    closest=_closest(hits), notice=f"{shown} is not mentioned in the documents I have. " + _who_to_ask(hits))
        return finish()

    # Layer 1: loose retrieval gate. Only stops questions that look unrelated to every document.
    best_cos = max((h.cosine for h in hits), default=0.0)
    best_overlap = max((h.overlap for h in hits), default=0)
    if not hits or (best_cos < config.GATE_MIN_COSINE and best_overlap == 0):
        resp.update(reason="gate: nothing in the documents resembles this question",
                    closest=_closest(hits), notice=_who_to_ask(hits))
        return finish()

    # Layer 2: the LLM answers only from the excerpts (or says it cannot).
    try:
        out = llm.generate_json(SYSTEM, build_user_prompt(question, hits))
    except llm.LLMUnavailable as e:
        # Degraded mode: show the matching document sections so the supervisor still gets something verifiable.
        resp.update(
            mode="retrieval_only", answerable=True, reason=f"llm unavailable: {e}",
            notice="The AI summary is not available right now. These are the matching sections of the plant documents.",
            # Without the LLM nothing can decide which sections matter, so show all of them as the source
            # (a lockout answer needs both the normal rule and the owner-absent exception).
            sources=[_source(i, h, qtokens, cited=True) for i, h in enumerate(hits, start=1)],
        )
        resp["safety_flag"] = any(h.chunk["has_safety_terms"] for h in hits[:2])
        resp["required"] = _required_evidence(hits, list(range(1, len(hits) + 1)), qtokens)
        for r in resp["required"]:
            resp["sources"][r["n"] - 1]["required"] = True
        resp["matched_row"] = _matched_row(hits, list(range(1, len(hits) + 1)), qtokens)
        resp["revision_notes"] = _revision_notes(retr, resp["sources"][:1])
        return finish()

    # Second look. A 3B model sometimes says "not answerable" for a plain value that is in the excerpt (the same
    # question answers correctly on the next try). If retrieval is very confident and the model refused with
    # nothing at all, ask once more with a nudge. The citation check below still applies, so this cannot invent
    # an answer, and the weakly matching unanswerable questions never reach this branch.
    refused_empty = not out.get("answerable") and not (out.get("answer") or "").strip() and not out.get("exceptions")
    if refused_empty and best_cos >= 0.70 and best_overlap >= 3:
        try:
            out2 = llm.generate_json(SYSTEM + RETRY_NOTE, build_user_prompt(question, hits))
            if out2.get("answerable") and (out2.get("answer") or "").strip():
                out = out2
                resp["reason"] = "second look: the model first refused although retrieval was confident"
        except llm.LLMUnavailable:
            pass

    # Layer 3: validate citations. An answer nobody can point to is treated as "not found".
    raw_cites = out.get("citations") or []
    model_cites = {int(c) for c in raw_cites if str(c).lstrip("-").isdigit() and 1 <= int(c) <= len(hits)}
    answer = (out.get("answer") or "").strip()
    exceptions = out.get("exceptions")
    if isinstance(exceptions, list):
        exceptions = " ".join(str(x) for x in exceptions)
    exceptions = (exceptions or "").strip()
    has_exceptions = bool(exceptions) and exceptions.lower() not in ("none", "n/a", "no exceptions", "null")
    # A model that writes an exception from the excerpts, names an excerpt, and still says "answerable: false"
    # has contradicted itself. Never answer "not found" to a question the documents cover: treat the
    # exception it found as the answer (it must still pass the citation check below).
    found_something = bool(out.get("answerable")) or (has_exceptions and bool(model_cites))
    if has_exceptions:
        answer = f"{answer}\n\n{exceptions}" if answer else exceptions
    # Small models often cite the wrong excerpt number. So the numbers are only a hint: an excerpt counts as
    # cited only if the answer text is actually found in it.
    named_ok = {c for c in model_cites if _supports(answer, hits[c - 1].chunk["text"], True)}
    strong = {c for c in range(1, len(hits) + 1) if _supports(answer, hits[c - 1].chunk["text"], False)}
    # Excerpts the model named (and the answer really matches) are the citations. Only if it named none that
    # fit do we fall back to the excerpts that strongly match the answer.
    cites = sorted(named_ok or strong)
    if not found_something or not answer:
        resp.update(reason="llm: excerpts do not contain the answer", closest=_closest(hits), notice=_who_to_ask(hits))
        return finish()
    if not cites:
        resp.update(reason="citation check: answer had no valid citation", closest=_closest(hits), notice=_who_to_ask(hits))
        return finish()

    answer = _restore_digits(answer, " ".join(hits[c - 1].chunk["text"] for c in cites))
    safety_flag = any(hits[c - 1].chunk["has_safety_terms"] for c in cites)
    # Safety net for small models. A rule must never travel without its exception just because the model
    # skipped it. For a safety answer, every other retrieved safety section of the same document that the
    # model did not cite is flagged "also read before you act".
    resp.update(mode="llm", answerable=True, answer=answer, safety_flag=safety_flag,
                sources=[_source(i, h, qtokens, cited=(i in cites)) for i, h in enumerate(hits, start=1)])
    resp["matched_row"] = _matched_row(hits, cites, qtokens)
    # Required evidence: the exception to any cited rule is shown verbatim, no matter what the model said.
    resp["required"] = _required_evidence(hits, cites, qtokens)
    required_ns = {r["n"] for r in resp["required"]}
    for s in resp["sources"]:
        s["required"] = s["n"] in required_ns
    if safety_flag:
        cited_docs = {hits[c - 1].chunk["doc_no"] for c in cites}
        for s in resp["sources"]:
            h = hits[s["n"] - 1]
            if not s["cited"] and not s["required"] and h.chunk["has_safety_terms"] and h.chunk["doc_no"] in cited_docs:
                s["also"] = True
    # cited first, then required, then "also read", then the rest (kept for transparency)
    resp["sources"].sort(key=lambda s: (not s["cited"], not s["required"], not s["also"], s["n"]))
    resp["revision_notes"] = _revision_notes(retr, [s for s in resp["sources"] if s["cited"]])
    return finish()
