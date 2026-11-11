"""FastAPI app.  Run:  uvicorn app.main:app --host 0.0.0.0 --port 8000"""
import json
import logging
import threading
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.rag import llm, pipeline
from app.schemas import AskRequest, AskResponse, FeedbackRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sop-copilot")

app = FastAPI(title="Shop-Floor SOP Copilot", version="1.0")


@app.on_event("startup")
def warm_up() -> None:
    """Load the index and the embedding model now, so the first question is not slow."""
    try:
        retr = pipeline.get_retriever()
        retr.embed_query("warm up")
        log.info("Index loaded: %d chunks", len(retr.chunks))
    except FileNotFoundError:
        log.error("Index not found. Run: python -m app.ingest.build_index")
    # Load the LLM into memory in the background so the first real question is not a 90-second wait.
    threading.Thread(target=_warm_llm, daemon=True).start()


def _warm_llm() -> None:
    try:
        t0 = time.time()
        llm.generate_json("Reply with JSON only.", '{"ok": true}')
        log.info("LLM warmed up in %.1fs", time.time() - t0)
    except Exception as e:  # noqa: BLE001 - the app also works without the model
        log.info("LLM warm-up skipped: %s", e)


@app.middleware("http")
async def no_cache_for_ui(request: Request, call_next):
    """The UI files change while we develop; without this a phone keeps showing the old page."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. Please try again."})


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        return pipeline.ask(req.question)
    except FileNotFoundError:
        raise HTTPException(503, "The document index has not been built yet. Run: python -m app.ingest.build_index")


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    """A supervisor's thumbs up / down on an answer. Stored next to the trace log for review and eval."""
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "trace_id": req.trace_id, "helpful": req.helpful}
    with (config.LOG_DIR / "feedback.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {"ok": True}


@app.get("/api/documents")
def documents():
    manifest = config.INDEX_DIR / "manifest.json"
    if not manifest.exists():
        raise HTTPException(503, "Index not built yet.")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    newest: dict[str, int] = {}
    for d in data["documents"]:
        newest[d["doc_no"]] = max(newest.get(d["doc_no"], -1), int(d["revision"]))
    for d in data["documents"]:
        d["status"] = "current" if int(d["revision"]) == newest[d["doc_no"]] else "superseded"
        d["pdf_url"] = f"/api/pdf/{d['file']}"
    return {"documents": data["documents"], "skipped_files": data.get("skipped_files", [])}


@app.get("/api/pdf/{filename}")
def pdf(filename: str):
    # Only serve files that were indexed, which also blocks path tricks like ../
    manifest = config.INDEX_DIR / "manifest.json"
    allowed = {d["file"] for d in json.loads(manifest.read_text(encoding="utf-8"))["documents"]} if manifest.exists() else set()
    if filename not in allowed:
        raise HTTPException(404, "Document not found")
    return FileResponse(config.PDF_DIR / filename, media_type="application/pdf")


@app.get("/api/health")
def health():
    index_ok = (config.INDEX_DIR / "chunks.json").exists()
    return {
        "index_loaded": index_ok,
        "chunks": len(pipeline.get_retriever().chunks) if index_ok else 0,
        "llm": llm.health(),
    }


@app.get("/")
def home():
    return FileResponse(config.STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
