from app.ai.agents.publisher import SlackPublisherAgent


class _RecordingSlackClient:
    def __init__(self) -> None:
        self.messages = []

    def post_message(self, channel, text, blocks=None, thread_ts=None):
        from app.integrations.slack_client import SlackMessageResult

        self.messages.append({"channel": channel, "text": text, "blocks": blocks,
                              "thread_ts": thread_ts})
        return SlackMessageResult(channel="C123", ts="111.222", permalink="https://slack/p1")


def _agent_and_client():
    client = _RecordingSlackClient()
    return SlackPublisherAgent(client), client  # type: ignore[arg-type]


def test_build_blocks_structure():
    agent, _ = _agent_and_client()
    blocks = agent.build_blocks(
        repository_name="demo",
        release_title="v1.1.0",
        range_summary="v1.0.0 → v1.1.0",
        slack_notes=":rocket: *Features*\n• Retries",
        risk_level="medium",
    )
    assert blocks[0]["type"] == "header"
    assert "v1.1.0" in blocks[0]["text"]["text"]
    assert any(b["type"] == "section" for b in blocks)
    context = blocks[1]["elements"][0]["text"]
    assert "MEDIUM" in context


def test_long_notes_are_truncated():
    agent, _ = _agent_and_client()
    blocks = agent.build_blocks("demo", "v1", "range", "x" * 5000, "low")
    section = next(b for b in blocks if b["type"] == "section")
    assert len(section["text"]["text"]) <= 3000


def test_publish_posts_thread_reply_with_markdown():
    agent, client = _agent_and_client()
    result = agent.publish(
        channel="#releases",
        repository_name="demo",
        release_title="v1.1.0",
        range_summary="v1.0.0 → v1.1.0",
        slack_notes="notes",
        risk_level="low",
        markdown_notes="# Full notes",
    )
    assert result.message_url == "https://slack/p1"
    assert len(client.messages) == 2
    assert client.messages[1]["thread_ts"] == "111.222"
