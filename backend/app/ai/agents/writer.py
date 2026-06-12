"""Release Writer agent: turns the change analysis into the four release-note
formats (executive, technical, markdown, slack)."""

from langchain_core.language_models.chat_models import BaseChatModel

from app.ai.prompts import WRITER_SYSTEM_PROMPT
from app.ai.schemas import ChangeAnalysis, ReleaseNotesDraft
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReleaseWriterAgent:
    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm.with_structured_output(ReleaseNotesDraft)

    def run(
        self,
        analysis: ChangeAnalysis,
        repository_name: str,
        release_title: str,
        range_summary: str,
        rag_context: str = "",
        reviewer_feedback: str | None = None,
    ) -> ReleaseNotesDraft:
        parts = [
            f"# Release metadata\nRepository: {repository_name}\n"
            f"Release title: {release_title}\nRange: {range_summary}\n",
            f"# Change analysis\n{analysis.model_dump_json(indent=2)}\n",
        ]
        if rag_context:
            parts.append(f"# Previous release notes (match tone/conventions)\n{rag_context}\n")
        if reviewer_feedback:
            parts.append(
                "# Reviewer feedback on your previous draft (MUST be addressed)\n"
                f"{reviewer_feedback}\n"
            )
        parts.append("Write the release notes in all four formats.")

        logger.info("writer_agent_start", revision=bool(reviewer_feedback))
        result: ReleaseNotesDraft = self._llm.invoke(
            [("system", WRITER_SYSTEM_PROMPT), ("user", "\n".join(parts))]
        )
        logger.info("writer_agent_done")
        return result
