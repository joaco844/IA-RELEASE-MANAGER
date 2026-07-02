from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BoardLabelOut(BaseModel):
    name: str
    color: str
    text_color: str
    description: str | None = None


class BoardIssueOut(BaseModel):
    iid: int
    title: str
    state: str
    labels: list[str] = []
    author_name: str | None = None
    assignee_names: list[str] = []
    milestone: str | None = None
    created_at: datetime | None = None
    closed_at: datetime | None = None
    web_url: str | None = None
    user_notes_count: int = 0


class BoardColumnOut(BaseModel):
    """One board column: the fixed Open/Closed columns or a label list."""

    key: str
    title: str
    type: Literal["open", "label", "closed"]
    list_id: int | None = None
    label: BoardLabelOut | None = None
    issues: list[BoardIssueOut] = []


class BoardOut(BaseModel):
    repository_id: int
    repository_name: str
    labels: list[BoardLabelOut] = []
    columns: list[BoardColumnOut] = []


class BoardListCreate(BaseModel):
    label: str = Field(min_length=1, max_length=255)


class BoardIssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=100_000)
    labels: list[str] = []


class BoardColumnRef(BaseModel):
    """Reference to a board column, used to describe issue moves."""

    type: Literal["open", "label", "closed"]
    label: str | None = Field(default=None, max_length=255)


class BoardIssueMove(BaseModel):
    from_column: BoardColumnRef
    to_column: BoardColumnRef


class BoardListOut(BaseModel):
    id: int
    label: str
    position: int
