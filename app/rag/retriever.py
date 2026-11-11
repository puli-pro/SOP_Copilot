"""Hybrid retrieval: BM25 + vector similarity, fused by rank (RRF), with revision filtering."""
import json
import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from app import config

STOP = set("""a an and are as at be by can do does for from how i in is it its me my of on or should so than that the
their then there this to up was we what when where which who whom why will with you your if not no""".split())

# Short forms a supervisor might type -> words that actually appear in the documents.
ABBREV = {
    "od": "outer diameter", "id": "inner diameter", "pm": "preventive maintenance",
    "loto": "lockout tagout", "mtc": "material test certificate", "sqe": "supplier quality engineer",
    "qc": "quality control", "cmm": "coordinate measuring machine", "ppe": "personal protective equipment",
    "scar": "supplier corrective action request", "qms": "quality management system",
}

OLD_REV_RE = re.compile(
    r"\b(rev(ision)?\.?\s*0?[1-3]\b|old(er)?|previous(ly)?|superseded|used to|changed|differences?)\b",
    re.I,
)
# Codes like AL-104, BH-220, QF-07A, SF-12, CNC-06. The valid prefixes are learned from the documents,
# so ordinary words followed by a number ("lot of 200") are never mistaken for a code.
CODE_IN_DOC_RE = re.compile(r"\b([A-Z]{1,4})-(\d{2,4}[A-Z]?)\b")
RANGE_RE = re.compile(r"\b([A-Z]{1,4})-(\d{2,4})\s+to\s+(?:[A-Z]{1,4}-)?(\d{2,4})\b")
CODE_PREFIXES: set[str] = {"al", "bh", "qf", "sf", "cnc"}


def _code_re():
    return re.compile(r"\b(" + "|".join(sorted(CODE_PREFIXES)) + r")\s?-?\s?(\d{2,4}[a-z]?)\b", re.I)


def normalise_query(q: str) -> str:
    """Make short, gloved-thumb queries match the documents: 'al104' -> 'al-104', 'od' -> 'outer diameter'."""
    q = q.strip()
    out = _code_re().sub(lambda m: f"{m.group(1)}-{m.group(2)}", q)
    words = re.findall(r"[A-Za-z0-9\-]+", out)
    extra = [ABBREV[w.lower()] for w in words if w.lower() in ABBREV]
    return (out + " " + " ".join(extra)).strip()


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())
    out = []
    for t in toks:
        out.append(t)
        if "-" in t:
            out.extend(p for p in t.split("-") if p)
    return [t for t in out if t not in STOP]


def wants_old_revisions(q: str) -> bool:
    return bool(OLD_REV_RE.search(q))


def load_embedder():
    """Use the locally cached embedding model first. Without this, a laptop with no internet (a plant
    Wi-Fi often has none) hangs at startup retrying huggingface.co even though the model is on disk."""
    from sentence_transformers import SentenceTransformer
    try:
        return SentenceTransformer(config.EMBED_MODEL, local_files_only=True)
    except Exception:  # not downloaded yet: fetch it (needs internet, first run only)
        return SentenceTransformer(config.EMBED_MODEL)


@dataclass
class Hit:
    chunk: dict
    rrf: float
    cosine: float
    bm25: float
    overlap: int  # number of distinct query tokens found in the chunk


class Retriever:
    def __init__(self, chunks: list[dict] | None = None, model=None):
        """Normally loads the saved index. The eval script passes its own chunks (and the already
        loaded embedding model) to compare chunking strategies."""
        self._model = model
        if chunks is None:
            self.chunks = json.loads((config.INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
            self.emb = np.load(config.INDEX_DIR / "embeddings.npy")
        else:
            self.chunks = chunks
            self.emb = np.asarray(
                self.model.encode([c["text_with_prefix"] for c in chunks], normalize_embeddings=True), dtype=np.float32
            )
        self.tokens = [tokenize(c["text_with_prefix"]) for c in self.chunks]
        self.known_codes = self._learn_codes()
        self.bm25 = BM25Okapi(self.tokens)

    def _learn_codes(self) -> set[str]:
        """Every code that literally appears in the documents, plus ranges like 'CNC-04 to CNC-09'."""
        codes: set[str] = set()
        for c in self.chunks:
            text = c["text"]
            for m in CODE_IN_DOC_RE.finditer(text):
                CODE_PREFIXES.add(m.group(1).lower())
                codes.add(f"{m.group(1)}-{m.group(2)}".lower())
            for m in RANGE_RE.finditer(text):
                width = len(m.group(2))
                for n in range(int(m.group(2)), int(m.group(3)) + 1):
                    codes.add(f"{m.group(1)}-{str(n).zfill(width)}".lower())
        return codes

    def unknown_codes(self, normalised_query: str) -> list[str]:
        """Codes the question names that appear in none of the documents (e.g. AL-999)."""
        found = re.findall(r"\b([a-z]{1,4}-\d{2,4}[a-z]?)\b", normalised_query.lower())
        return [c for c in found if c.split("-")[0] in CODE_PREFIXES and c not in self.known_codes]

    @property
    def model(self):
        if self._model is None:
            self._model = load_embedder()
        return self._model

    def embed_query(self, q: str) -> np.ndarray:
        return self.model.encode([config.QUERY_PREFIX + q], normalize_embeddings=True)[0]

    def search(self, question: str, k: int = config.TOP_K, include_superseded: bool | None = None) -> tuple[list[Hit], dict]:
        if include_superseded is None:
            include_superseded = wants_old_revisions(question)
        nq = normalise_query(question)
        qtok = tokenize(nq)
        allowed = np.array([include_superseded or c["status"] == "current" for c in self.chunks])

        bm = np.array(self.bm25.get_scores(qtok)) if qtok else np.zeros(len(self.chunks))
        cos = self.emb @ self.embed_query(nq)
        bm = np.where(allowed, bm, -1e9)
        cos_masked = np.where(allowed, cos, -1e9)

        n = config.CANDIDATES
        bm_rank = [i for i in np.argsort(-bm)[:n] if allowed[i] and bm[i] > 0]
        vec_rank = [i for i in np.argsort(-cos_masked)[:n] if allowed[i]]
        rrf: dict[int, float] = {}
        for ranks in (bm_rank, vec_rank):
            for r, i in enumerate(ranks):
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (config.RRF_K + r + 1)
        order = sorted(rrf, key=lambda i: -rrf[i])[:k]

        qset = set(qtok)
        hits = [
            Hit(self.chunks[i], rrf[i], float(cos[i]), float(bm[i]), len(qset & set(self.tokens[i])))
            for i in order
        ]
        info = {"normalised_query": nq, "include_superseded": include_superseded}
        return hits, info

    def add_linked(self, hits: list[Hit], question: str, include_superseded: bool, limit: int = 5) -> list[Hit]:
        """If a retrieved chunk points to another SOP (e.g. hose replacement -> SAF-SOP-003) and that SOP
        is not in the results, add its best-matching chunk. Keeps cross-document answers complete."""
        have_docs = {h.chunk["doc_no"] for h in hits}
        known = {c["doc_no"] for c in self.chunks}
        wanted = []
        for h in hits:
            for doc in re.findall(r"\b[A-Z]{2,4}-(?:SOP|MAN)-[A-Z0-9\-]*\d+\b", h.chunk["text"]):
                if doc in known and doc not in have_docs and doc not in wanted:
                    wanted.append(doc)
        if not wanted or len(hits) >= limit:
            return hits
        qvec = self.embed_query(normalise_query(question))
        cos = self.emb @ qvec
        for doc in wanted:
            idx = [i for i, c in enumerate(self.chunks)
                   if c["doc_no"] == doc and (include_superseded or c["status"] == "current")]
            if not idx or len(hits) >= limit:
                continue
            best = max(idx, key=lambda i: cos[i])
            hits.append(Hit(self.chunks[best], 0.0, float(cos[best]), 0.0, 0))
        return hits
