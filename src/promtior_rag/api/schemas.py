"""Pydantic schemas for the chat API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatInput(BaseModel):
    """Input payload for the chat endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User question about Promtior.",
        examples=["What services does Promtior offer?"],
    )


class ChatOutput(BaseModel):
    """Output payload for the chat endpoint."""

    answer: str = Field(..., description="Generated answer with source citations.")