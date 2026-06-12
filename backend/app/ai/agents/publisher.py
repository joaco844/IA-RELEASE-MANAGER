"""Slack Publisher agent: formats the release as Slack Block Kit, publishes it
and returns the publication URL (plus a thread reply linking the full notes)."""

from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.integrations.slack_client import SlackClient

logger = get_logger(__name__)

_SLACK_TEXT_LIMIT = 2900  # Block Kit section text hard limit is 3000


@dataclass
class SlackPublication:
    channel: str
    message_url: str
    ts: str


class SlackPublisherAgent:
    def __init__(self, client: SlackClient) -> None:
        self._client = client

    def build_blocks(
        self,
        repository_name: str,
        release_title: str,
        range_summary: str,
        slack_notes: str,
        risk_level: str | None,
        release_url: str | None = None,
    ) -> list[dict[str, Any]]:
        risk_emoji = {"low": ":large_green_circle:", "medium": ":large_yellow_circle:",
                      "high": ":red_circle:"}.get(risk_level or "", ":white_circle:")
        body = slack_notes.strip()
        if len(body) > _SLACK_TEXT_LIMIT:
            body = body[:_SLACK_TEXT_LIMIT] + "…"

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f":rocket: {release_title}"[:150]},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*{repository_name}* · {range_summary} · "
                        f"{risk_emoji} risk: *{(risk_level or 'unknown').upper()}*",
                    }
                ],
            },
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": body}},
        ]
        if release_url:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"<{release_url}|View full release notes>"}
                    ],
                }
            )
        return blocks

    def publish(
        self,
        channel: str,
        repository_name: str,
        release_title: str,
        range_summary: str,
        slack_notes: str,
        risk_level: str | None,
        markdown_notes: str | None = None,
        release_url: str | None = None,
    ) -> SlackPublication:
        blocks = self.build_blocks(
            repository_name, release_title, range_summary, slack_notes, risk_level, release_url
        )
        fallback = f"{release_title} — {repository_name} ({range_summary})"
        result = self._client.post_message(channel=channel, text=fallback, blocks=blocks)

        # Thread reply with the full markdown notes for readers who want detail.
        if markdown_notes:
            snippet = markdown_notes.strip()
            if len(snippet) > _SLACK_TEXT_LIMIT:
                snippet = snippet[:_SLACK_TEXT_LIMIT] + "…"
            try:
                self._client.post_message(
                    channel=result.channel,
                    text=snippet,
                    thread_ts=result.ts,
                )
            except Exception:  # noqa: BLE001 - thread reply is best-effort
                logger.warning("slack_thread_reply_failed", channel=result.channel)

        logger.info("slack_publish_done", channel=result.channel, permalink=result.permalink)
        return SlackPublication(
            channel=result.channel, message_url=result.permalink, ts=result.ts
        )
