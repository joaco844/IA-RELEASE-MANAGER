"""Slack integration: workspace verification and message publishing."""

from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SlackTeamInfo:
    team_id: str
    team_name: str


@dataclass
class SlackMessageResult:
    channel: str
    ts: str
    permalink: str


class SlackClient:
    def __init__(self, bot_token: str) -> None:
        from slack_sdk import WebClient  # lazy: keeps unit tests free of the dependency
        from slack_sdk.errors import SlackApiError

        self._SlackApiError = SlackApiError
        self._client = WebClient(token=bot_token)

    def verify_token(self) -> SlackTeamInfo:
        try:
            response = self._client.auth_test()
            return SlackTeamInfo(
                team_id=str(response.get("team_id", "")),
                team_name=str(response.get("team", "")),
            )
        except self._SlackApiError as exc:
            raise ExternalServiceError(f"Slack token verification failed: {exc}") from exc

    def post_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str | None = None,
    ) -> SlackMessageResult:
        """Post a message (optionally as a thread reply) and return its permalink."""
        try:
            response = self._client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
                thread_ts=thread_ts,
                unfurl_links=False,
            )
            posted_channel = str(response["channel"])
            ts = str(response["ts"])
            permalink = ""
            try:
                link_response = self._client.chat_getPermalink(
                    channel=posted_channel, message_ts=ts
                )
                permalink = str(link_response.get("permalink", ""))
            except self._SlackApiError:
                logger.warning("slack_permalink_failed", channel=posted_channel, ts=ts)
            return SlackMessageResult(channel=posted_channel, ts=ts, permalink=permalink)
        except self._SlackApiError as exc:
            raise ExternalServiceError(f"Slack publish failed: {exc}") from exc
