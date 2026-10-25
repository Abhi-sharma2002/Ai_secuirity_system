"""Strict active answer contracts; wire schemas are preserved."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Answer(Strict):
    status: Literal['answered', 'insufficient_evidence', 'conflict']
    answer: str
    source_ids: list[str]

    @field_validator('answer')
    @classmethod
    def usable_answer_text(cls, text):
        # Keep the wire schema stable; validate meaningful text locally without rewriting it.
        if not text.strip():
            raise ValueError('blank_answer')
        return text
