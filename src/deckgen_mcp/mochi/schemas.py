from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Deck(BaseModel):
    id: str
    name: str
    parent_id: str | None = Field(default=None, alias="parent-id")
    trashed: str | None = Field(default=None, alias="trashed?")

    model_config = {"populate_by_name": True}


class Card(BaseModel):
    id: str
    content: str
    deck_id: str = Field(alias="deck-id")
    template_id: str | None = Field(default=None, alias="template-id")
    fields: dict[str, Any] = Field(default_factory=dict)
    trashed: str | None = Field(default=None, alias="trashed?")

    model_config = {"populate_by_name": True}


class Template(BaseModel):
    id: str
    name: str
    content: str
    fields: dict[str, Any] = Field(default_factory=dict)


class ListResponse(BaseModel):
    docs: list[dict]
    bookmark: str | None = None
