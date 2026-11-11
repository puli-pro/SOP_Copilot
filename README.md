# SOP Copilot

A mobile-friendly question-answering app for shop-floor supervisors. It answers from the plant's SOPs and
manuals (4 PDFs in `Files/`), shows the exact source (document, **revision**, section, page, text), says so
when the answer is not in the documents, and always prefers the **current** revision.

Stack: FastAPI, PyMuPDF, `bge-small-en-v1.5` embeddings, BM25 + vector search fused with RRF, Ollama (`qwen2.5:3b`, a 1.9 GB model that runs well on a 6 GB laptop GPU), plain HTML/JS UI.
Why these choices, and what I left out: see [FINAL_PLAN.md](FINAL_PLAN.md) and [THINKING.md](THINKING.md).

## Setup (Windows, Python 3.11)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5:3b           # about 1.9 GB; set OLLAMA_MODEL in .env to try a bigger one (llama3.1:8b, qwen2.5:7b)
python -m app.ingest.build_index # parses the PDFs and builds the index (first run downloads a 130 MB embedding model)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`. Without the Ollama model the app still runs in **search-only mode**: it shows the
matching document sections and the status pill says "AI offline: search only".

Optional settings go in `.env` (see `.env.example`).

## Open it from your phone (same Wi-Fi)

1. Start the server with `--host 0.0.0.0` (as above). The default `127.0.0.1` is the usual reason a phone cannot connect.
2. Find the laptop's IP: `ipconfig` → "Wi-Fi" → IPv4 address (on my laptop it was `10.199.122.65`).
3. Allow the port through Windows Firewall (run PowerShell **as Administrator** once; Windows marks home Wi-Fi as "Public" by default, which blocks inbound traffic):
   ```powershell
   New-NetFirewallRule -DisplayName "SOP Copilot 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any
   ```
4. On the phone (same Wi-Fi) open `http://<laptop-ip>:8000`.
5. If it still does not load, the router may isolate clients (common on office/college Wi-Fi). Use the phone's hotspot and connect the laptop to it.
6. Warm up the model with one question before demoing: the first Ollama call is slow.

## How it answers

```
question → normalise ("al305" → "AL-305", "OD" → "outer diameter")
         → unknown-code check (AL-999 is in no document → "not found", no LLM call)
         → hybrid retrieval: BM25 + vectors, rank fusion, current revisions only (top 4)
           + linked documents (hose replacement pulls in the lockout SOP)
         → loose relevance gate (nothing resembles the question → "not found")
         → LLM answers only from numbered excerpts, returns JSON {answerable, answer, citations}
         → citation check (no valid citation → "not found")
         → answer + source cards (revision badge, section, page, exact text, "Open PDF at page N")
```

**The improvement I added: revision awareness.** `QC-SOP-014` is supplied twice (Rev 03 from 2023 and Rev 04 from 2026)
and they disagree (sample size, quarantine location, form, escalation, certificate rule). Each chunk carries its
revision and status; superseded chunks are excluded unless the question asks about an old revision; every source
shows its revision and effective date, and superseded sources carry a red warning. Safety-related answers
(lockout, stored energy) also get a "confirm against the SOP page" banner.

Chunking: one chunk per numbered section, tables kept whole as Markdown with their header row, tables that run onto the next page merged, page recorded per line (so AL-104 links to page 2). 28 chunks in total.

## Endpoints

`POST /api/ask` · `POST /api/feedback` (thumbs up/down on an answer) · `GET /api/documents` · `GET /api/pdf/{file}#page=N` · `GET /api/health` · interactive docs at `/docs`.
Every request appends a line to `logs/trace.jsonl` (question, retrieved chunks with scores, mode, latency); feedback goes to `logs/feedback.jsonl`, keyed by the same `trace_id`.

The UI is plain HTML/CSS/JS in `app/static/` (no build step). Its patterns (thinking indicator, rounded prompt bar, source chips, answer action row) were chosen after browsing 21st.dev's AI-chat components and re-written by hand.

## Evaluation

```bash
python -m eval.run_eval      # writes eval/results.md and eval/results.json
```

Current results are in [eval/results.md](eval/results.md). Retrieval (no LLM needed): evidence hit@4 100% vs 81% for a
fixed-size baseline; no superseded chunk retrieved for current-revision questions. The answer-level part (key facts,
citations, false-accept / false-reject, latency) runs only once the Ollama model is installed. 22 questions over 7 pages is a sanity check, not a benchmark.

## My 5 questions and the app's answers

Sample questions are in `Files/Sample_Questions.pdf`. My own five, with one the documents cannot answer:

| # | Question | Why I chose it | App's answer |
|---|---|---|---|
| 1 | How many samples do I need to inspect from a lot of 200 pieces? | Rev 03 says 5, Rev 04 says 13 | _fill after running with the model_ |
| 2 | How do I replace a hydraulic hose? | Needs two documents; must include lockout | _fill after running with the model_ |
| 3 | Where do I put rejected material? | Rev 03 and Rev 04 differ | _fill after running with the model_ |
| 4 | What happens if the material test certificate is missing? | Rule changed in Rev 04 | _fill after running with the model_ |
| 5 | What is the maximum spindle speed of the TX-200? | Plausible but **not in the documents** | _fill after running with the model_ |

## Known limits

- Seven pages is not a real knowledge base; thresholds are tuned on a handful of questions.
- Questions that are close to the documents but not covered (e.g. "overheating warning") are only caught by the LLM's refusal and the citation check, not by the gate. This is measured in the eval once the model is installed.
- English only. No login, no history, no offline cache.
- Information only: it does not replace the approvals the SOPs require.
