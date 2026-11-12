from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class FeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=4, max_length=32, pattern=r"^[a-z0-9]+$")
    helpful: bool


class RequiredEvidence(BaseModel):
    """An exception section that must be shown because the answer rests on the rule it qualifies."""
    n: int
    kind: str = "exception"  # "exception" (to a cited rule) or "rule" (that a cited exception qualifies)
    doc_no: str
    revision: str
    section: str
    page: int
    page_range: list[int]
    text: str
    pdf_url: str
    qualifies: str  # the cited section this one belongs with


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
    also: bool = False  # a safety section the model did not cite but the supervisor should still read
    required: bool = False  # an exception section that is shown deterministically (see RequiredEvidence)
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
    required: list[RequiredEvidence] = []
    sources: list[Source]
    closest: list[Closest]
    revision_notes: list[str]
    notice: str
    reason: str
    latency_ms: int
