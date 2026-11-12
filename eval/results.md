# Evaluation results

Run: 2026-11-12 11:22 | embedding model `BAAI/bge-small-en-v1.5` | LLM `qwen2.5:3b` (used) | 18 answerable + 6 unanswerable questions over 7 pages (a sanity check, not a benchmark). Key facts are checked against what the supervisor sees: the AI's answer plus the blocks the app copies verbatim from the document (the matching table row and any required exception).

## A. Retrieval: structure-aware chunks vs fixed-size baseline (no LLM involved)

| Metric | Structure-aware (mine) | Fixed 500-char baseline |
|---|---|---|
| Evidence hit@1 (all evidence in the top chunk) | 13/18 (72%) | 9/18 (50%) |
| Evidence hit@4 (all evidence in the top 4) | 18/18 (100%) | 14/18 (78%) |
| MRR (rank of first chunk with the key evidence) | 0.94 | 0.65 |
| Chunks in index | 28 | 27 |

- **Superseded-revision leak (retrieval):** 0/17 questions that did not ask for an old revision retrieved a Rev 03 chunk.
- **Gate and unknown-code check:** stopped 3/6 unanswerable questions before the LLM, and wrongly blocked 0/18 answerable ones.

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
| L1 | Can a supervisor take off another person's lock? | - / Y (first rank 1) | - / - (first rank none) |
| L2 | How do I apply my lock before maintenance? | Y / Y (first rank 1) | Y / Y (first rank 1) |

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

| Metric | Result |
|---|---|
| Key facts visible on screen (AI answer + verbatim table row + required exception) | 18/18 (100%) |
| ...for comparison: key facts in the AI's own sentence alone | 15/18 (83%) |
| Citation accuracy (a cited source contains the evidence) | 18/18 (100%) |
| False-accept rate (answered an unanswerable question) | 0/6 (0%) |
| False-reject rate (refused an answerable question) | 0/18 (0%) |
| Superseded-revision leak (cited a Rev 03 source) | 0/17 |
| "Open PDF at page N" points to the right page (answers that sit on page 2) | 5/5 |
| Required exception shown (safety rule + its exception, enforced by the app) | 2/2 |
| ...for comparison: exception present in the AI's own answer text | 0/2 |
| Exception blocks shown where not needed | 0 (none) |
| Latency p50 / p95 (this laptop) | 2538 ms / 5251 ms |

| ID | Mode | Result |
|---|---|---|
| S1 | llm | fact ok, cite ok |
| S2 | llm | fact ok, cite ok |
| S3 | llm | fact ok, cite ok |
| S4 | llm | fact ok, cite ok |
| S5 | llm | fact ok, cite ok |
| X1 | llm | fact ok, cite ok |
| X2 | llm | fact ok, cite ok |
| X3 | llm | fact ok, cite ok |
| X4 | llm | fact ok, cite ok |
| X5 | llm | fact ok, cite ok |
| R1 | llm | fact ok, cite ok |
| R2 | llm | fact ok, cite ok |
| R3 | llm | fact ok, cite ok |
| R4 | llm | fact ok, cite ok |
| R5 | llm | fact ok, cite ok |
| R6 | llm | fact ok, cite ok |
| L1 | llm | fact ok, cite ok |
| L2 | llm | fact ok, cite ok |
| N1 | not_found | refused (correct) |
| N2 | not_found | refused (correct) |
| N3 | not_found | refused (correct) |
| N4 | not_found | refused (correct) |
| N5 | not_found | refused (correct) |
| N6 | not_found | refused (correct) |
