# Evaluation results

Run: 2026-11-11 16:48 | embedding model `BAAI/bge-small-en-v1.5` | LLM `llama3.1:8b` (NOT installed, so answer-level metrics were not run) | 16 answerable + 6 unanswerable questions over 7 pages (a sanity check, not a benchmark).

## A. Retrieval: structure-aware chunks vs fixed-size baseline (no LLM involved)

| Metric | Structure-aware (mine) | Fixed 500-char baseline |
|---|---|---|
| Evidence hit@1 (all evidence in the top chunk) | 12/16 (75%) | 8/16 (50%) |
| Evidence hit@4 (all evidence in the top 4) | 16/16 (100%) | 13/16 (81%) |
| MRR (rank of first chunk with the key evidence) | 0.94 | 0.67 |
| Chunks in index | 28 | 27 |

- **Superseded-revision leak (retrieval):** 0/15 questions that did not ask for an old revision retrieved a Rev 03 chunk.
- **Gate and unknown-code check:** stopped 3/6 unanswerable questions before the LLM, and wrongly blocked 0/16 answerable ones.

Per question (hit@1 / hit@4, structured | baseline):

| ID | Question | Structured | Baseline |
|---|---|---|---|
| S1 | What is the recommended coolant concentration for the TX-200 CNC turni | - / Y (first rank 2) | - / Y (first rank 2) |
| S2 | The machine is showing alarm AL-104. What does it mean and what should | Y / Y (first rank 1) | Y / Y (first rank 1) |
| S3 | Who is allowed to remove a lockout lock from a machine? | - / Y (first rank 1) | - / - (first rank none) |
| S4 | What is the outer diameter tolerance for the BH-220 bearing housing? | Y / Y (first rank 1) | - / Y (first rank 2) |
| S5 | How often should spindle runout be checked, and who does it? | Y / Y (first rank 1) | Y / Y (first rank 1) |
| X1 | AL-305 | Y / Y (first rank 1) | Y / Y (first rank 1) |
| X2 | al305 on CNC-06 | Y / Y (first rank 1) | - / Y (first rank 2) |
| X3 | bh220 od | Y / Y (first rank 1) | Y / Y (first rank 1) |
| X4 | What is the torque for the chuck mounting bolts? | Y / Y (first rank 1) | - / Y (first rank 3) |
| X5 | What oil is used for the yearly hydraulic oil change? | Y / Y (first rank 1) | Y / Y (first rank 1) |
| R1 | How many samples do I need to inspect from a lot of 200 pieces? | Y / Y (first rank 1) | Y / Y (first rank 1) |
| R2 | Where do I put rejected material? | Y / Y (first rank 1) | - / Y (first rank 3) |
| R3 | What happens if the material test certificate is missing? | Y / Y (first rank 1) | - / - (first rank none) |
| R4 | How many samples did the old procedure require? | Y / Y (first rank 1) | Y / Y (first rank 1) |
| R5 | How do I replace a hydraulic hose? | - / Y (first rank 1) | - / - (first rank 2) |
| R6 | Who holds the key to the quarantine cage? | - / Y (first rank 2) | Y / Y (first rank 1) |

Unanswerable questions, before the LLM:

| ID | Question | Stopped before LLM | Unknown code | Best cosine | Best word overlap |
|---|---|---|---|---|---|
| N1 | What is the overheating warning procedure? | no (LLM must refuse) | - | 0.589 | 1 |
| N2 | What is the maximum spindle speed of the TX-200? | no (LLM must refuse) | - | 0.57 | 3 |
| N3 | What does alarm AL-999 mean? | yes | al-999 | 0.618 | 2 |
| N4 | What is the torque for the CNC-12 spindle bearing? | yes | cnc-12 | 0.651 | 2 |
| N5 | What is the weather today? | yes | - | 0.508 | 0 |
| N6 | How many days of annual leave do employees get? | no (LLM must refuse) | - | 0.576 | 1 |

## B. Full pipeline (retrieve, gate, LLM, citation check)

Not run: the Ollama model `llama3.1:8b` is not installed on this machine yet (`ollama pull llama3.1:8b`, then rerun `python -m eval.run_eval`).

Search-only latency for reference (retrieval + gate, no LLM): p50 179 ms, p95 202 ms.
