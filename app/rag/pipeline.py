"""The question -> answer flow: retrieve, gate, ask the LLM, validate citations, build the response."""
import json
import re
import time
import uuid
from datetime import datetime, timezone

from app import config
from app.rag import llm
from app.rag.prompts import SYSTEM, build_user_prompt
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
    best, best_score = pages[0], -1
    for line, pg in zip(lines, pages):
        score = len(qtokens & set(tokenize(line)))
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
        "score": round(hit.rrf, 4),
    }


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
    qtokens = set(tokenize(info["normalised_query"]))

    resp: dict = {
        "trace_id": trace_id, "question": question, "answerable": False, "mode": "not_found",
        "answer": "", "safety_flag": False, "sources": [], "closest": [], "revision_notes": [],
        "notice": "", "reason": "",
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
            "citations": [s["n"] for s in resp["sources"] if s["cited"]], "latency_ms": resp["latency_ms"],
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
        resp["revision_notes"] = _revision_notes(retr, resp["sources"][:1])
        return finish()

    # Layer 3: validate citations. An answer nobody can point to is treated as "not found".
    raw_cites = out.get("citations") or []
    model_cites = {int(c) for c in raw_cites if str(c).lstrip("-").isdigit() and 1 <= int(c) <= len(hits)}
    answer = (out.get("answer") or "").strip()
    exceptions = out.get("exceptions")
    if isinstance(exceptions, list):
        exceptions = " ".join(str(x) for x in exceptions)
    exceptions = (exceptions or "").strip()
    if exceptions and exceptions.lower() not in ("none", "n/a", "no exceptions", "null") and answer:
        answer = f"{answer}\n\n{exceptions}"
    # Small models often cite the wrong excerpt number. So the numbers are only a hint: an excerpt counts as
    # cited only if the answer text is actually found in it.
    named_ok = {c for c in model_cites if _supports(answer, hits[c - 1].chunk["text"], True)}
    strong = {c for c in range(1, len(hits) + 1) if _supports(answer, hits[c - 1].chunk["text"], False)}
    # Excerpts the model named (and the answer really matches) are the citations. Only if it named none that
    # fit do we fall back to the excerpts that strongly match the answer.
    cites = sorted(named_ok or strong)
    if not out.get("answerable") or not answer:
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
    if safety_flag:
        cited_docs = {hits[c - 1].chunk["doc_no"] for c in cites}
        for s in resp["sources"]:
            h = hits[s["n"] - 1]
            if not s["cited"] and h.chunk["has_safety_terms"] and h.chunk["doc_no"] in cited_docs:
                s["also"] = True
    # cited first, then "also read", then the rest (kept for transparency)
    resp["sources"].sort(key=lambda s: (not s["cited"], not s["also"], s["n"]))
    resp["revision_notes"] = _revision_notes(retr, [s for s in resp["sources"] if s["cited"]])
    return finish()
