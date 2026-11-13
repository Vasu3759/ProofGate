from datetime import datetime
from pydantic import BaseModel, Field


class FactOut(BaseModel):
    id: str
    fact_key: str
    version: int
    label: str
    claim_text: str
    owner: str
    approval_status: str
    source_name: str
    source_version: str
    effective_at: datetime


class FactCreate(BaseModel):
    fact_key: str = Field(min_length=2, max_length=100)
    label: str = Field(min_length=2, max_length=160)
    claim_text: str = Field(min_length=4, max_length=2000)
    source_name: str = Field(min_length=2, max_length=200)
    source_version: str = Field(default="v1.0", min_length=1, max_length=40)
    owner: str = Field(min_length=2, max_length=160)


class SubmissionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    channel: str = Field(default="Marketing", max_length=100)
    content: str = Field(min_length=5, max_length=20000)


class RevisionCreate(BaseModel):
    content: str = Field(min_length=5, max_length=20000)


class DecisionCreate(BaseModel):
    decision: str
    comments: str = Field(default="", max_length=4000)
    override_justification: str | None = Field(default=None, max_length=2000)
