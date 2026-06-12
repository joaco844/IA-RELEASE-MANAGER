from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.release import ReleaseOut


class RepositoryConnect(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    gitlab_url: str = Field(examples=["https://gitlab.com"], max_length=500)
    project_path: str = Field(examples=["group/project"], max_length=500)
    access_token: str = Field(min_length=8, max_length=500)


class RepositoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gitlab_url: str
    project_path: str
    default_branch: str | None
    description: str | None
    last_release_at: datetime | None = None
    created_at: datetime


class RepositoryDetailOut(RepositoryOut):
    recent_releases: list[ReleaseOut] = []
