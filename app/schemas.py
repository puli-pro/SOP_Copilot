from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class FeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=4, max_length=32, pattern=r"^[a-z0-9]+$")
    helpful: bool


class Source(BaseModel):
    n: int
    doc_no: str
    title: str
    revision: str
    effective_date: str
    status: str  # "current" or "superseded"
    section: str
    page: int
    page_range: list[int]
    text: str
    file: str
    pdf_url: str
    cited: bool
    score: float


class Closest(BaseModel):
    doc_no: str
    title: str
    revision: str
    file: str
    pdf_url: str


class AskResponse(BaseModel):
    trace_id: str
    question: str
    answerable: bool
    mode: str  # "llm" | "retrieval_only" | "not_found"
    answer: str
    safety_flag: bool
    sources: list[Source]
    closest: list[Closest]
    revision_notes: list[str]
    notice: str
    reason: str
    latency_ms: int
