from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SlackConnect(BaseModel):
    bot_token: str = Field(min_length=8, max_length=500)
    default_channel: str = Field(default="#releases", max_length=255)


class SlackWorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_name: str | None
    default_channel: str
    connected_at: datetime


class SlackPublishRequest(BaseModel):
    release_id: int
    channel: str | None = None


class SlackPublishOut(BaseModel):
    message_url: str
    channel: str
    published_at: datetime
