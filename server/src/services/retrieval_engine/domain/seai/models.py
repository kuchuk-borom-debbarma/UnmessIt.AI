from pydantic import BaseModel, Field


class Citation(BaseModel):
    statement_id: str
    source_input_id: str = ""
    start_char: int = 0
    end_char: int = 0
    exact_quote: str


class CitedAnswer(BaseModel):
    answer_text: str
    citations: list[Citation]


class RetrievalPlan(BaseModel):
    intent: str = "answer"
    answer_style: str = "concise"
    search_queries: list[str] = Field(default_factory=list)
    must_find: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class EvidenceScore(BaseModel):
    evidence_id: str
    score: float = 0.0
    reason: str = ""


class RerankDecision(BaseModel):
    selected_evidence_ids: list[str] = Field(default_factory=list)
    scores: list[EvidenceScore] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)
    follow_up_queries: list[str] = Field(default_factory=list)
    enough_evidence: bool = False
