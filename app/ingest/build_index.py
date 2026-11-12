"""Build the search index.  Usage:  python -m app.ingest.build_index

PDFs -> parsed sections -> chunks (+ revision status) -> embeddings. Writes to index/.
"""
import hashlib
import json
import sys
import time

import numpy as np

from app import config
from app.ingest.chunk import chunk_document, link_exceptions
from app.ingest.parse import parse_pdf


def load_and_chunk(verbose: bool = True):
    parsed_docs, skipped = [], []
    for pdf in sorted(config.PDF_DIR.glob("*.pdf")):
        d = parse_pdf(pdf)
        if d is None:
            skipped.append(pdf.name)
            continue
        parsed_docs.append(d)

    # Revision status: for each document number, the highest revision is current.
    newest: dict[str, int] = {}
    for d in parsed_docs:
        newest[d["doc_no"]] = max(newest.get(d["doc_no"], -1), int(d["revision"]))

    chunks = []
    for d in parsed_docs:
        status = "current" if int(d["revision"]) == newest[d["doc_no"]] else "superseded"
        for c in chunk_document(d):
            c["status"] = status
            chunks.append(c)
        if verbose:
            print(f"  {d['doc_no']} Rev {d['revision']} ({status}): {len([c for c in chunks if c['file'] == d['file']])} chunks")
    pairs = link_exceptions(chunks)
    if verbose:
        for c in chunks:
            if c["qualified_by"]:
                print(f"  exception link: {c['chunk_id']} ({c['section_title']}) <- {', '.join(c['qualified_by'])}")
        print(f"  {pairs} rule/exception pair(s) linked")
    if verbose and skipped:
        print("  skipped (no 'Document No.' header):", ", ".join(skipped))
    return parsed_docs, chunks, skipped


def main():
    t0 = time.time()
    print("Parsing PDFs from", config.PDF_DIR)
    parsed_docs, chunks, skipped = load_and_chunk()
    if not chunks:
        sys.exit("No SOP chunks produced; check PDF_DIR.")

    print(f"Embedding {len(chunks)} chunks with {config.EMBED_MODEL} ...")
    from app.rag.retriever import load_embedder

    model = load_embedder()
    emb = model.encode([c["text_with_prefix"] for c in chunks], normalize_embeddings=True, show_progress_bar=False)

    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    (config.INDEX_DIR / "chunks.json").write_text(json.dumps(chunks, indent=1, ensure_ascii=False), encoding="utf-8")
    np.save(config.INDEX_DIR / "embeddings.npy", np.asarray(emb, dtype=np.float32))
    manifest = {
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "embed_model": config.EMBED_MODEL,
        "chunk_count": len(chunks),
        "skipped_files": skipped,
        "documents": [
            {"file": d["file"], "doc_no": d["doc_no"], "revision": d["revision"],
             "effective_date": d["effective_date"], "title": d["title"], "pages": d["pages"],
             "sha256": hashlib.sha256((config.PDF_DIR / d["file"]).read_bytes()).hexdigest()}
            for d in parsed_docs
        ],
    }
    (config.INDEX_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"Done in {time.time() - t0:.1f}s. Index written to {config.INDEX_DIR}")


if __name__ == "__main__":
    main()
