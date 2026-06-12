from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_slack_service
from app.schemas.slack import (
    SlackConnect,
    SlackPublishOut,
    SlackPublishRequest,
    SlackWorkspaceOut,
)
from app.services.slack_service import SlackService

router = APIRouter(prefix="/slack", tags=["slack"])

SlackSvc = Annotated[SlackService, Depends(get_slack_service)]


@router.post("/connect", response_model=SlackWorkspaceOut, status_code=status.HTTP_201_CREATED)
def connect_workspace(
    payload: SlackConnect, user: CurrentUser, service: SlackSvc
) -> SlackWorkspaceOut:
    return SlackWorkspaceOut.model_validate(service.connect(user, payload))


@router.get("/workspace", response_model=SlackWorkspaceOut)
def get_workspace(user: CurrentUser, service: SlackSvc) -> SlackWorkspaceOut:
    return SlackWorkspaceOut.model_validate(service.get_workspace(user))


@router.post("/publish", response_model=SlackPublishOut)
def publish_release(
    payload: SlackPublishRequest, user: CurrentUser, service: SlackSvc
) -> SlackPublishOut:
    release = service.publish(user, payload)
    return SlackPublishOut(
        message_url=release.slack_message_url or "",
        channel=release.slack_channel or "",
        published_at=release.slack_published_at,
    )
