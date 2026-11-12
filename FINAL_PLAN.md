# My Plan: Shop-Floor SOP Copilot

I started from two draft architectures: a heavy one (Docling parsing, BGE-M3 embeddings, a reranker, a Qdrant vector database, HyDE query expansion, Ragas evaluation) and a light one (PyMuPDF, a small embedding model, BM25 plus vectors, plain NumPy). I chose the light one and revised it after reading the four PDFs and the sample questions in `Files/`: seven pages and a 6 GB laptop do not need the heavy one (section 5 lists what I left out and why). I used AI tools to help compare options; the decisions below are the ones I am going with and can explain.

> **Status: this is the plan I wrote before building.** What changed once the app was running (all measured in [eval/results.md](eval/results.md) and explained in [THINKING.md](THINKING.md)):
> - The model is `qwen2.5:3b` (1.9 GB), not `llama3.1:8b`; it is fast on the laptop and `OLLAMA_MODEL` in `.env` can switch it.
> - Testing showed a small model gives half answers on safety rules and slips on table lookups, so I added things the app enforces itself instead of trusting the model: required evidence (a rule and its exception always shown word for word), the matching table row copied from the PDF, a citation check on the answer text, a "second look" when the model refuses despite confident retrieval, and a fix for the PDF page link.
> - The chunking, revision handling and not-found layers below were built as planned. The schedule in section 8 is the original plan, not a record of what happened.

## 1. What I found in the documents

| What I saw | What it means for my design |
|---|---|
| 4 PDFs, **7 pages total**, about 28 numbered sections, all digital text | I don't need OCR, Docling or a vector database. About 30 chunks. |
| **QC-SOP-014 is there twice: Rev 03 (2023) and Rev 04 (effective 01-Jul-2026)**, and they contradict each other | The biggest risk in the project. See section 3. |
| Sections and tables run across page breaks (alarm table p1→p2; Rev 04 "5. Procedure" heading on p1, steps on p2) | I chunk by section, never by page. |
| Tables carry the key facts (operating parameters, PM schedule, alarms, sampling plan, BH-220 dimensions) | I keep each table whole, with its header row. |
| Exact codes matter: AL-305, QF-07A, SF-12, BH-220, ISO VG 46 vs VG 68 | I add keyword search (BM25) next to vectors. |
| Documents reference each other (hose replacement → SAF-SOP-003) | I retrieve the top 4 so both documents can appear. |
| Every footer says "Uncontrolled copy when printed. Refer to QMS for the latest version." | I strip it from chunks; it is noise on every page. |

Rev 03 vs Rev 04 conflicts (a question on any of these has two different "answers" in the corpus):

| Topic | Rev 03 (superseded) | Rev 04 (current) |
|---|---|---|
| Sample size | 5 from every lot | By lot size (all / 5 / 13 / 32 / 50) |
| Rejected material goes to | Red Bin area near Gate 2 | Quarantine Cage Q1, Stores Bay 3 |
| Inspection record | Paper form QF-07, kept 2 years | Digital form QF-07A, kept 5 years |
| Escalation | Email Purchase by end of shift | Inform SQE within 4 hours |
| Material test certificate | "if available" | Mandatory, lot on HOLD without it |

### What the five sample questions test

| # | Question | Expected answer | Source | What it stresses |
|---|---|---|---|---|
| 1 | Coolant concentration for the TX-200? | 6 – 8 % | MNT-MAN-CNC-02 §3, p.1 | Value inside a table row |
| 2 | Alarm AL-104: meaning and action? | Way lube oil level low. Top up with ISO VG 68 to the MAX mark, press RESET; machine can continue. | MNT-MAN-CNC-02 §6, **p.2** | Exact code match; the row is on page 2 while the table heading is on page 1 |
| 3 | Who may remove a lockout lock? | Each authorised person removes only their own lock. If the owner is absent: Shift Supervisor tries to phone them, then the Production Manager and Safety Officer must both authorise, machine inspected, recorded on SF-12. | SAF-SOP-003 §5 and §6, p.1–2 | A complete answer needs **two sections** |
| 4 | Outer diameter tolerance for BH-220? | +/- 0.050 mm (nominal 90.000) | QC-SOP-014 **Rev 04** §6, p.2 | Picking the right table row; neighbouring rows have different tolerances |
| 5 | How often is spindle runout checked, and by whom? | Monthly, by the maintenance technician | MNT-MAN-CNC-02 §4, p.1 | "Spindle runout" also appears in §3 (0.005 mm max), which is the wrong section here |

What these changed in my design:

- **`Sample_Questions.pdf` must not be indexed.** It sits next to the SOPs. If I ingested it, the questions themselves would come back as the best "source". My ingestion only accepts PDFs with a `Document No.` header block.
- **Tables become Markdown rows** (PyMuPDF `find_tables`), so `Outer diameter | 90.000 | +/- 0.050 | Digital caliper | Major` stays on one line. Plain text extraction puts each cell on its own line, which a small local model misreads.
- **A table that continues on the next page is merged**, and the repeated header row is dropped.
- **Each chunk records the page of every line**, so the source card for AL-104 says page 2.
- **The prompt asks for conditions and exceptions from all relevant excerpts**, so question 3 returns both the rule and the owner-absent procedure.

None of the sample questions touches the Rev 03 / Rev 04 conflict, so one of my own five will.

## 2. Architecture

```
INGEST (run once)
 PDFs (only those with a "Document No." header) → PyMuPDF text + tables per page
      → strip header/footer lines; tables → Markdown rows; merge tables split across pages
      → read doc number, revision, effective date from the header block
      → split on numbered section headings (joined across pages, page kept per line)
      → mark lower revisions of the same doc number as SUPERSEDED
      → embed (bge-small-en-v1.5) → save chunks.json + embeddings.npy

QUERY
 Phone UI → POST /api/ask
   1. Hybrid retrieve: BM25 + cosine similarity, fused by rank (RRF), top 4
      (superseded chunks excluded unless the question asks about an old revision)
   2. Loose retrieval gate: clearly off-topic → "not found", no LLM call
   3. LLM (Ollama) with numbered excerpts → JSON {answerable, answer, citations}
   4. Citation check: no valid citation → "not found"
   5. Response: answer + source cards (doc number, revision, section, page, snippet)
   6. Append one line to a JSONL trace log
```

| Layer | My choice | Reason |
|---|---|---|
| API | FastAPI + uvicorn on `0.0.0.0:8000` | Required by the brief |
| Parsing | PyMuPDF only (text + `find_tables`) | All pages have a clean text layer; tables have ruled borders |
| Chunking | One chunk per numbered section, tables kept whole | See section 4 |
| Embeddings | `BAAI/bge-small-en-v1.5` (130 MB, CPU) | See section 5 |
| Vector search | NumPy cosine over ~30 vectors | A vector DB adds nothing at this size |
| Keyword search | `rank_bm25` | Alarm codes, form numbers, part numbers |
| LLM | Ollama `llama3.1:8b`; `qwen2.5:3b` as fallback | Fits my 6 GB GPU; local is a bonus in the brief |
| UI | One static HTML page, mobile-first | No build step |
| Eval | My own script, results written to a Markdown table | See section 6 |

## 3. Revision handling (must have)

- Each chunk stores `doc_no`, `revision`, `effective_date`, `status` (`current` or `superseded`).
- Default retrieval uses current chunks only.
- If the question mentions a revision, "old", "previous" or "changed", superseded chunks are included and labelled.
- Every source card shows the revision and effective date. Superseded sources get a red "Superseded" badge.

Without this, "How many samples do I draw from a lot of 200?" can return 5 (Rev 03) when the right answer is 13 (Rev 04).

## 4. Chunking: nine strategies, one choice

| Strategy | Verdict | Why |
|---|---|---|
| Fixed-size | No (baseline only) | Cuts numbered steps and tables in half |
| Recursive character | No | Better than fixed, still blind to tables |
| Sentence-based | No | A table row or one step alone has no meaning |
| Sliding window / overlap | Not needed | Sections are self-contained; overlap only duplicates |
| Semantic (embedding breakpoints) | No | Extra compute to rediscover headings that are already printed |
| **Document-structure (by heading)** | **Yes** | Every document uses numbered sections of 50–300 tokens |
| **Table-aware** | **Yes, combined** | Tables stay whole inside their section with the header row |
| Hierarchical (parent–child) | No | Sections are already small enough to pass whole |
| LLM / agentic chunking | No | Slow, non-deterministic, hard to explain |

Each chunk gets a prefix, for example `[QC-SOP-014 Rev 04 | 4. Sampling Plan | p.1]`.

To back the choice with a number, my eval script also runs a fixed-size baseline (500 characters) and reports retrieval hit rate for both.

## 5. Embeddings and the rest of the basics

- **Embedding model:** `bge-small-en-v1.5`. With about 30 chunks, a larger model (BGE-M3) cannot show a measurable gain and costs 2.3 GB.
- **Hybrid search:** kept. It is about 20 lines and handles codes like `AL-210` that vectors blur.
- **Reranker, HyDE, query rewriting, Qdrant/Chroma, Docling, OCR, Ragas, LangChain:** dropped. I list each in THINKING.md under "left out, and why", with the condition under which it would come back (hundreds of SOPs, scanned pages).
- **Not-found handling:** the LLM's `answerable` flag plus the citation check do the real work. The similarity gate only catches clearly off-topic questions, because a threshold tuned on 30 chunks is not reliable.

## 6. Evaluation and metrics

`eval/questions.json`: about 15–20 labelled questions (the five samples with the expected answers above, my five own questions, version-conflict questions, unanswerable ones). Each has expected document, section, key facts (e.g. `110 Nm`), and an `answerable` flag.

`eval/run_eval.py` writes `eval/results.md`, which goes into the README:

| Metric | What it shows |
|---|---|
| Retrieval hit@1 / hit@4, MRR | Did the right section come back, and how high |
| Same, for the fixed-size baseline | Evidence for my chunking choice |
| Key-fact accuracy | Does the answer contain the expected value |
| Citation accuracy | Does the cited section match the expected one |
| False-accept rate | Answered a question the documents cannot answer |
| False-reject rate | Refused a question the documents can answer |
| Superseded-leak rate | Answered from Rev 03 when Rev 04 applies |
| Latency p50 / p95 | Per-question response time on my laptop |

A limit I will state openly: 15–20 questions on 7 pages is a sanity check, not a benchmark.

## 7. The one improvement

It has to follow from my own user journey. Two candidates the documents support:

1. **Revision awareness** (badge, effective date, superseded warning). Backed by the Rev 03/Rev 04 conflict and the "uncontrolled copy when printed" footer.
2. **Safety callout** on LOTO and stored-energy answers, with "confirm against the SOP page".

I build revision filtering either way, because it is a correctness issue. Only the visible part (badge and warning) would count as the improvement.

## 8. Complete project, step by step

Deadline: Thursday 12 November, 11:59 PM.

### Track A: writing (in THINKING.md)

| Step | Task | Done when |
|---|---|---|
| A1 | "Understand the user": who the supervisor is, what they are trying to do, what frustrates them, with my assumptions. AI and research are allowed for this step. | Half a page, checked and edited by me |
| A2 | User-journey first draft, step by step, including what could go wrong. **Written by me, before using AI**, as the brief asks. I keep the untouched draft. | Draft saved before A3 |
| A3 | AI challenge: an AI critiques my journey as a skeptical user or product manager. I save the conversation. | Key excerpts copied out |
| A4 | Reflection: what I agreed with, disagreed with, and changed. | Short section plus the revised journey |
| A5 | Pick the one improvement from the journey. | One sentence: what and why |

A5 is decided before step B6.

### Track B: the build

| Step | Task | Done when | Time |
|---|---|---|---|
| B0 | Setup: folder layout, virtual environment, `requirements.txt`, `.gitignore`, `git init`, pull the Ollama model | `ollama run llama3.1:8b` answers; packages import | 20 min |
| B1 | Ingest: parse PDFs, tables to Markdown, section chunks, revision metadata, embeddings | About 30 chunks; Rev 03 marked superseded; `Sample_Questions.pdf` skipped; AL-104 row shows page 2 | 50 min |
| B2 | Retrieval: BM25 + vectors + rank fusion + revision filter, run from the command line | All five sample questions return the expected section in the top 4 | 30 min |
| B3 | Answering: prompt, JSON contract, citation check, not-found path | Five sample questions answered correctly; an undocumented question returns "not found" | 40 min |
| B4 | FastAPI endpoints (`/api/ask`, `/api/pdf/{doc}`, `/api/health`) and the trace log | `/docs` works; each request adds a line to the log | 20 min |
| B5 | Mobile UI: input, sample-question chips, answer card, source cards with revision and "open PDF at page", not-found state | Usable in a phone-width browser window | 40 min |
| B6 | The one improvement chosen in A5 | Visible in the UI and demoable in ten seconds | 20 min |
| B7 | Evaluation: `questions.json`, eval script, fixed-size baseline, `results.md` | Results table generated with all metrics from section 6 | 30 min |
| B8 | Local network: run on `0.0.0.0:8000`, allow the port in Windows Firewall, open from my phone | App answers a question on my phone | 15 min |

My five questions (B7) will include one that hits the Rev 03 / Rev 04 conflict, one that needs two documents (hose replacement plus lockout), and at least one plausible question the documents cannot answer (an alarm code or machine that is not documented).

### Track C: submission

| Step | Task | Done when |
|---|---|---|
| C1 | README: setup, run, phone access, my five questions with the app's actual answers, the results table | A stranger could run it from the README alone |
| C2 | THINKING.md: the five required sections, including the final reflection (what next, what I am unsure about, questions for the customer, biggest challenge) | All five headings from the brief present |
| C3 | Public GitHub repo, pushed, checked while logged out; no `.env` or index files committed | Complete: public repository confirmed |
| C4 | Screen recording, 2–3 minutes: two sample questions, one unanswerable question, the app on my phone | Verified complete (2:44): [local file](Final_Demo_Video.mp4); [Google Drive link](https://drive.google.com/file/d/1mmNGQSG6C15NXcAygfkw_-LQO1EEUMzt/view?usp=sharing) |
| C5 | Reply to BiztelAI with the repo link and recording link | Complete: reply sent |

The completed recording shows the AL-104 maintenance answer and source page, BH-220 outer-diameter tolerance from QC-SOP-014 Rev 04 (±0.050 mm), the unanswerable maximum-spindle-speed question and Not Found response, the Lockout/Tagout rule that each authorised person removes only their own lock plus the owner-absent authorisation exception, and the same app accessed from a phone over local Wi-Fi.

Stretch, only if time remains: Dockerfile; safety callout if not chosen as the improvement.

## 9. Fit against Project_Prd.md

| PRD item | Status |
|---|---|
| FastAPI + simple UI + RAG over the PDFs | Covered |
| Source document shown | Covered (doc number, revision, section, page, snippet) |
| Says so when the answer is not in the documents | Covered (LLM flag + citation check + gate) |
| One improvement from the user journey | Covered: revision awareness, including current-revision handling |
| Runs on laptop, opened from phone on same Wi-Fi | Covered (bind `0.0.0.0`, firewall rule, hotspot fallback) |
| Local LLM (bonus) | Covered: `qwen2.5:3b` run locally |
| Docker (bonus) | Stretch only |
| Test with the sample questions | Covered; all five are answerable, expected answers in section 1 |
| 5 own questions with answers in README | Covered by the eval script |
| Steps 1–2: understand the user, user journey | Complete in THINKING.md, sections 1–2 |
| Step 3: AI challenge and reflection | Complete in THINKING.md, section 3 |
| Step 6: final reflection | Complete in THINKING.md, section 5 |
| Public GitHub repo, screen recording | Public repository and submission reply are complete. The 2:44 recording is available locally at [Final_Demo_Video.mp4](Final_Demo_Video.mp4) and via [Google Drive](https://drive.google.com/file/d/1mmNGQSG6C15NXcAygfkw_-LQO1EEUMzt/view?usp=sharing). All the Current documentation edits and updates are pushed to the public repository |

## 10. If this had hundreds of SOPs: what I would add, and what would trigger it

Two earlier drafts of this plan included heavier components. I left them out because seven digital pages do not need them, not because I did not consider them. This is the order I would add them in a real plant, and the signal that would justify each one.

| Need | What I would add | What would trigger it | Why it is not in this app |
|---|---|---|---|
| Scanned or complex PDFs | OCR and a layout-aware parser (for example Docling, Surya or PaddleOCR) | Pages with no text layer, or tables the current parser mangles | All four PDFs have a clean text layer and ruled tables, and PyMuPDF reads them correctly |
| Many more documents | A vector database with metadata filters by machine, area and document type, so search is narrowed before ranking | Thousands of chunks, or answers drifting to the wrong machine's SOP | About 30 chunks fit in plain NumPy, and a database adds a service to run |
| Ranking quality | A cross-encoder reranker over the top 15 to 20 results; its score could also drive the "not found" decision | The right section is retrieved but not near the top | Evidence was in the top 4 for every test question |
| Vocabulary gap between supervisors and SOPs | Query rewriting or hypothetical-answer search, only when retrieval is unsure (it costs an extra model call) | Short or slangy queries that miss the right section | Code matching and abbreviation expansion covered the test queries |
| Which revision is in force | Document status read from the plant's QMS instead of inferred from revision numbers | A newer revision exists that is not in the folder | I only have the PDFs I was given (stated as a limit in THINKING.md) |
| Knowing it works | A much larger labelled question set, evaluation tooling, and review of the thumbs-down feedback the app already stores | Any real rollout | 26 questions is a sanity check, not a benchmark (stated in the README) |
| Real users | Login and role-based access, answers in the supervisor's language, and an offline mode | The customer's answers to the questions in THINKING.md | Out of scope for the assignment |
