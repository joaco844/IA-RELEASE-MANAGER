from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationFailedError
from app.core.logging import audit_log
from app.core.security import TokenCipher
from app.models import Release, ReleaseStatus, SlackWorkspace, User
from app.repositories.releases import ReleaseRepository
from app.repositories.slack_workspaces import SlackWorkspaceRepository
from app.schemas.slack import SlackConnect, SlackPublishRequest


class SlackService:
    def __init__(
        self,
        session: Session,
        slack_client_factory: Any = None,
        publisher_factory: Any = None,
    ) -> None:
        self.workspaces = SlackWorkspaceRepository(session)
        self.releases = ReleaseRepository(session)
        self._cipher = TokenCipher()
        if slack_client_factory is None:
            from app.integrations.slack_client import SlackClient

            slack_client_factory = SlackClient
        self._slack_factory = slack_client_factory
        if publisher_factory is None:
            from app.ai.agents.publisher import SlackPublisherAgent

            publisher_factory = SlackPublisherAgent
        self._publisher_factory = publisher_factory

    def connect(self, user: User, payload: SlackConnect) -> SlackWorkspace:
        client = self._slack_factory(payload.bot_token)
        team = client.verify_token()

        workspace = self.workspaces.get_for_owner(user.id)
        if workspace is None:
            workspace = SlackWorkspace(owner_id=user.id, encrypted_bot_token="")
            self.workspaces.add(workspace)
        workspace.team_id = team.team_id
        workspace.team_name = team.team_name
        workspace.encrypted_bot_token = self._cipher.encrypt(payload.bot_token)
        workspace.default_channel = payload.default_channel
        workspace.connected_at = datetime.now(UTC)
        self.workspaces.commit()
        audit_log("slack_connected", user_id=user.id, team=team.team_name)
        return workspace

    def get_workspace(self, user: User) -> SlackWorkspace:
        workspace = self.workspaces.get_for_owner(user.id)
        if workspace is None:
            raise NotFoundError("Slack workspace is not connected")
        return workspace

    def publish(self, user: User, payload: SlackPublishRequest) -> Release:
        workspace = self.get_workspace(user)
        release = self.releases.get_for_owner(payload.release_id, user.id)
        if release is None:
            raise NotFoundError("Release not found")
        if release.status not in (
            ReleaseStatus.COMPLETED.value,
            ReleaseStatus.PUBLISHED.value,
        ):
            raise ValidationFailedError(
                "Release notes are not ready to publish (status: " f"{release.status})"
            )
        if not release.slack_notes:
            raise ValidationFailedError("Release has no Slack-formatted notes")

        channel = payload.channel or workspace.default_channel
        token = self._cipher.decrypt(workspace.encrypted_bot_token)
        publisher = self._publisher_factory(self._slack_factory(token))
        publication = publisher.publish(
            channel=channel,
            repository_name=release.repository.name,
            release_title=release.title,
            range_summary=release.range_summary,
            slack_notes=release.slack_notes,
            risk_level=release.risk_level,
            markdown_notes=release.markdown_notes,
        )

        release.slack_channel = publication.channel
        release.slack_message_url = publication.message_url
        release.slack_published_at = datetime.now(UTC)
        release.status = ReleaseStatus.PUBLISHED.value
        self.releases.commit()
        audit_log(
            "release_published_to_slack",
            user_id=user.id,
            release_id=release.id,
            channel=channel,
        )
        return release
