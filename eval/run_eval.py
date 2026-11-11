"""Evaluation.  Usage:  python -m eval.run_eval

Writes eval/results.md and eval/results.json.

Part A (always runs, needs no LLM): retrieval quality of the structure-aware chunks vs a fixed-size
        baseline, superseded-revision leakage, and how many unanswerable questions are stopped
        before the LLM.
Part B (runs only if the Ollama model is installed): answer quality, citations, false accept /
        reject rate and latency of the full pipeline.

"Evidence" for a question is one or more exact strings from the PDFs. A retrieval hit@k means every
evidence string appears in the union of the top-k chunks. Using text evidence (not chunk ids) lets
both chunking strategies be scored on the same footing.
"""
import json
import re
import statistics
import time
from pathlib import Path

import fitz

from app import config
from app.ingest.build_index import load_and_chunk
from app.ingest.chunk import fixed_size_chunks
from app.rag import llm, pipeline
from app.rag.retriever import Retriever, tokenize

HERE = Path(__file__).parent


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).lower().strip()


def has(text: str, needle: str) -> bool:
    return norm(needle) in norm(text)


def evidence_rank(hits, evidence) -> dict:
    texts = [h.chunk["text"] for h in hits]
    first = next((i + 1 for i, t in enumerate(texts) if has(t, evidence[0])), None)
    union = lambda k: " ".join(texts[:k])
    return {
        "first_rank": first,
        "hit1": all(has(texts[0], e) for e in evidence) if texts else False,
        "hit4": all(has(union(4), e) for e in evidence),
    }


def baseline_chunks(parsed_docs):
    meta = {}
    newest = {}
    for d in parsed_docs:
        newest[d["doc_no"]] = max(newest.get(d["doc_no"], -1), int(d["revision"]))
    for d in parsed_docs:
        doc = fitz.open(config.PDF_DIR / d["file"])
        lines = []
        for page in doc:
            for ln in page.get_text().split("\n"):
                if "Uncontrolled copy when printed" in ln or re.fullmatch(r"Page \d+", ln.strip()):
                    continue
                lines.append(ln)
        meta[f"{d['doc_no']}-r{d['revision']}"] = {
            "text": "\n".join(lines), "doc_no": d["doc_no"], "revision": d["revision"], "title": d["title"],
            "effective_date": d["effective_date"], "file": d["file"],
            "status": "current" if int(d["revision"]) == newest[d["doc_no"]] else "superseded",
        }
    return fixed_size_chunks(meta, size=500, overlap=0)


def pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "n/a"


def main():
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    answerable = [q for q in questions if q["answerable"]]
    unanswerable = [q for q in questions if not q["answerable"]]

    retr = pipeline.get_retriever()
    parsed_docs, _, _ = load_and_chunk(verbose=False)
    base = Retriever(chunks=baseline_chunks(parsed_docs), model=retr.model)

    # ---------- Part A: retrieval ----------
    rows, stats = [], {"structured": {"h1": 0, "h4": 0, "rr": 0.0}, "baseline": {"h1": 0, "h4": 0, "rr": 0.0}}
    leaks, gate_stopped = 0, 0
    non_hist = [q for q in answerable if not q.get("historical")]
    for q in answerable:
        row = {"id": q["id"], "question": q["question"]}
        for name, r in (("structured", retr), ("baseline", base)):
            hits, info = r.search(q["question"])
            if name == "structured":
                hits = r.add_linked(hits, q["question"], info["include_superseded"])
            m = evidence_rank(hits, q["evidence"])
            stats[name]["h1"] += m["hit1"]
            stats[name]["h4"] += m["hit4"]
            stats[name]["rr"] += 1 / m["first_rank"] if m["first_rank"] else 0
            row[name] = m
            if name == "structured" and not q.get("historical"):
                leaks += any(h.chunk["status"] == "superseded" for h in hits)
                row["leak"] = any(h.chunk["status"] == "superseded" for h in hits)
        rows.append(row)

    # ---------- gate behaviour on unanswerable questions ----------
    gate_rows = []
    for q in unanswerable:
        hits, info = retr.search(q["question"])
        unknown = retr.unknown_codes(info["normalised_query"])
        best_cos = max((h.cosine for h in hits), default=0)
        best_ov = max((h.overlap for h in hits), default=0)
        stopped = bool(unknown) or (best_cos < config.GATE_MIN_COSINE and best_ov == 0)
        gate_stopped += stopped
        gate_rows.append({"id": q["id"], "question": q["question"], "stopped_before_llm": stopped,
                          "unknown_codes": unknown, "best_cos": round(best_cos, 3), "best_overlap": best_ov})
    # also check the gate never blocks an answerable question
    wrongly_blocked = 0
    for q in answerable:
        hits, info = retr.search(q["question"])
        unknown = retr.unknown_codes(info["normalised_query"])
        best_cos = max((h.cosine for h in hits), default=0)
        best_ov = max((h.overlap for h in hits), default=0)
        wrongly_blocked += bool(unknown) or (best_cos < config.GATE_MIN_COSINE and best_ov == 0)

    # ---------- Part B: full pipeline (needs the LLM) ----------
    health = llm.health()
    llm_ready = health["reachable"] and health["model_ready"]
    answers = []
    latencies = []
    for q in questions:
        t0 = time.time()
        resp = pipeline.ask(q["question"])
        latencies.append((time.time() - t0) * 1000)
        answers.append((q, resp))
    full = None
    if llm_ready:
        ok_fact = ok_cite = false_accept = false_reject = 0
        leak_answer = 0
        detail = []
        for q, resp in answers:
            if q["answerable"]:
                text = norm(resp["answer"])
                fact = resp["mode"] == "llm" and all(norm(m) in text for m in q["must_include"])
                cited = [s for s in resp["sources"] if s["cited"]]
                cite_ok = any(all(has(s["text"], e) for e in [ev]) for s in cited for ev in q["evidence"][:1])
                if resp["mode"] != "llm":
                    false_reject += 1
                ok_fact += fact
                ok_cite += cite_ok
                if not q.get("historical") and any(s["status"] == "superseded" for s in cited):
                    leak_answer += 1
                detail.append({"id": q["id"], "mode": resp["mode"], "fact_ok": fact, "cite_ok": cite_ok})
            else:
                false_accept += resp["mode"] == "llm"
                detail.append({"id": q["id"], "mode": resp["mode"], "refused": resp["mode"] != "llm"})
        full = {"fact": ok_fact, "cite": ok_cite, "false_accept": false_accept, "false_reject": false_reject,
                "leak": leak_answer, "detail": detail}

    # ---------- write results ----------
    n_a, n_u = len(answerable), len(unanswerable)
    lat_sorted = sorted(latencies)
    p50 = statistics.median(latencies)
    p95 = lat_sorted[min(len(lat_sorted) - 1, int(0.95 * len(lat_sorted)))]
    md = []
    md.append("# Evaluation results\n")
    md.append(f"Run: {time.strftime('%Y-%m-%d %H:%M')} | embedding model `{config.EMBED_MODEL}` | "
              f"LLM `{config.OLLAMA_MODEL}` ({'used' if llm_ready else 'NOT installed, so answer-level metrics were not run'}) | "
              f"{n_a} answerable + {n_u} unanswerable questions over 7 pages (a sanity check, not a benchmark).\n")
    md.append("## A. Retrieval: structure-aware chunks vs fixed-size baseline (no LLM involved)\n")
    md.append("| Metric | Structure-aware (mine) | Fixed 500-char baseline |\n|---|---|---|")
    for label, key in (("Evidence hit@1 (all evidence in the top chunk)", "h1"), ("Evidence hit@4 (all evidence in the top 4)", "h4")):
        md.append(f"| {label} | {stats['structured'][key]}/{n_a} ({pct(stats['structured'][key], n_a)}) | {stats['baseline'][key]}/{n_a} ({pct(stats['baseline'][key], n_a)}) |")
    md.append(f"| MRR (rank of first chunk with the key evidence) | {stats['structured']['rr'] / n_a:.2f} | {stats['baseline']['rr'] / n_a:.2f} |")
    md.append(f"| Chunks in index | {len(retr.chunks)} | {len(base.chunks)} |")
    md.append("")
    md.append(f"- **Superseded-revision leak (retrieval):** {leaks}/{len(non_hist)} questions that did not ask for an old revision retrieved a Rev 03 chunk.\n"
              f"- **Gate and unknown-code check:** stopped {gate_stopped}/{n_u} unanswerable questions before the LLM, and wrongly blocked {wrongly_blocked}/{n_a} answerable ones.\n")
    md.append("Per question (hit@1 / hit@4, structured | baseline):\n")
    md.append("| ID | Question | Structured | Baseline |\n|---|---|---|---|")
    for r in rows:
        f = lambda m: f"{'Y' if m['hit1'] else '-'} / {'Y' if m['hit4'] else '-'} (first rank {m['first_rank'] or 'none'})"
        md.append(f"| {r['id']} | {r['question'][:70]} | {f(r['structured'])} | {f(r['baseline'])} |")
    md.append("\nUnanswerable questions, before the LLM:\n")
    md.append("| ID | Question | Stopped before LLM | Unknown code | Best cosine | Best word overlap |\n|---|---|---|---|---|---|")
    for g in gate_rows:
        md.append(f"| {g['id']} | {g['question'][:60]} | {'yes' if g['stopped_before_llm'] else 'no (LLM must refuse)'} | {', '.join(g['unknown_codes']) or '-'} | {g['best_cos']} | {g['best_overlap']} |")

    md.append("\n## B. Full pipeline (retrieve, gate, LLM, citation check)\n")
    if full:
        md.append("| Metric | Result |\n|---|---|")
        md.append(f"| Key-fact accuracy (answerable) | {full['fact']}/{n_a} ({pct(full['fact'], n_a)}) |")
        md.append(f"| Citation accuracy (a cited source contains the evidence) | {full['cite']}/{n_a} ({pct(full['cite'], n_a)}) |")
        md.append(f"| False-accept rate (answered an unanswerable question) | {full['false_accept']}/{n_u} ({pct(full['false_accept'], n_u)}) |")
        md.append(f"| False-reject rate (refused an answerable question) | {full['false_reject']}/{n_a} ({pct(full['false_reject'], n_a)}) |")
        md.append(f"| Superseded-revision leak (cited a Rev 03 source) | {full['leak']}/{len(non_hist)} |")
        md.append(f"| Latency p50 / p95 (this laptop) | {p50:.0f} ms / {p95:.0f} ms |")
        md.append("\n| ID | Mode | Result |\n|---|---|---|")
        for d in full["detail"]:
            res = ("fact ok" if d.get("fact_ok") else "FACT MISSING") + (", cite ok" if d.get("cite_ok") else ", CITE WRONG") if "fact_ok" in d else ("refused (correct)" if d["refused"] else "ANSWERED (wrong)")
            md.append(f"| {d['id']} | {d['mode']} | {res} |")
    else:
        md.append(f"Not run: the Ollama model `{config.OLLAMA_MODEL}` is not installed on this machine yet "
                  f"(`ollama pull {config.OLLAMA_MODEL}`, then rerun `python -m eval.run_eval`).\n")
        md.append(f"Search-only latency for reference (retrieval + gate, no LLM): p50 {p50:.0f} ms, p95 {p95:.0f} ms.")

    (HERE / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (HERE / "results.json").write_text(json.dumps({"retrieval": rows, "gate": gate_rows, "full": full}, indent=1), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
