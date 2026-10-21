"""Shared persisted value contracts; evaluator labels are absent from runtime evidence."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

State = Literal['received','validating','parsing','parsed','indexing','ready','rejected','needs_ocr','needs_review','failed','deleted']


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ParsedBlock(Contract):
    text: str
    page: int = Field(ge=0)
    section: str


class ParsedDocument(Contract):
    blocks: list[ParsedBlock]
    warnings: list[str]
    status: Literal['parsed','needs_ocr','needs_review']
    parser_version: str


class DocumentVersion(Contract):
    id: str
    document_id: str
    filename: str
    sha256: str = Field(pattern='^[a-f0-9]{64}$')
    status: State
    created: datetime
    index_name: str | None
    expected_version: str | None
    blocks: list[ParsedBlock] = []
    warnings: list[str] = []
    parser_version: str | None = None
    partial_accepted: bool = False
    error: str | None = None


class RetrievalHit(Contract):
    id: str
    document_id: str
    version_id: str
    sha256: str
    filename: str
    text: str
    page: int
    section: str
    partial_text: bool
    distance: float
