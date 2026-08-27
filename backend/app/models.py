from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    slide_count: int | None = None


class SuggestionUpdate(BaseModel):
    status: Literal["pending", "accepted", "rejected", "edited"]
    edited_action: str | None = None


class RevisionPlanRequest(BaseModel):
    suggestion_ids: list[str]


class JobStepResponse(BaseModel):
    key: str
    label: str
    status: str
    error: str | None = None


class SuggestionResponse(BaseModel):
    id: str
    slide_number: int
    category: str
    severity: str
    title: str
    description: str
    action: str
    rationale: str
    automation: str
    status: str
    edited_action: str | None = None


class JobResponse(BaseModel):
    id: str
    project_id: str
    status: str
    current_step: str | None
    steps: list[JobStepResponse]
    storyline: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
