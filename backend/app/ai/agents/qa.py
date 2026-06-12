"""QA agent: validates generated notes against source data, detecting
hallucinations and enforcing traceability before publication."""

from langchain_core.language_models.chat_models import BaseChatModel

from app.ai.prompts import QA_SYSTEM_PROMPT
from app.ai.schemas import QAVerdict, ReleaseNotesDraft
from app.core.logging import get_logger

logger = get_logger(__name__)


class QAAgent:
    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm.with_structured_output(QAVerdict)

    def run(self, notes: ReleaseNotesDraft, source_digest: str) -> QAVerdict:
        user_prompt = (
            f"# Source data digest\n\n{source_digest}\n\n"
            f"# Generated release notes\n\n"
            f"## Executive\n{notes.executive}\n\n"
            f"## Technical\n{notes.technical}\n\n"
            f"## Markdown\n{notes.markdown}\n\n"
            f"## Slack\n{notes.slack}\n\n"
            "Review the notes against the source data and return your verdict."
        )
        logger.info("qa_agent_start")
        verdict: QAVerdict = self._llm.invoke(
            [("system", QA_SYSTEM_PROMPT), ("user", user_prompt)]
        )
        logger.info(
            "qa_agent_done",
            approved=verdict.approved,
            traceability=verdict.traceability_score,
            issues=len(verdict.issues_found),
        )
        return verdict
