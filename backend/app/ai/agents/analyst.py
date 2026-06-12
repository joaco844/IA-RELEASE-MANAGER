"""Repository Analyst agent: understands commits, groups related changes,
detects themes and classifies everything with impact + risk."""

from langchain_core.language_models.chat_models import BaseChatModel

from app.ai.context import source_data_digest
from app.ai.prompts import ANALYST_SYSTEM_PROMPT
from app.ai.schemas import ChangeAnalysis
from app.core.logging import get_logger
from app.integrations.gitlab_client import CommitData, IssueData, MergeRequestData

logger = get_logger(__name__)


class RepositoryAnalystAgent:
    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm.with_structured_output(ChangeAnalysis)

    def run(
        self,
        commits: list[CommitData],
        merge_requests: list[MergeRequestData],
        issues: list[IssueData],
        rag_context: str = "",
    ) -> ChangeAnalysis:
        digest = source_data_digest(commits, merge_requests, issues)
        user_prompt = (
            f"# Source data for this release\n\n{digest}\n\n"
            + (
                f"# Historical context (previous releases)\n\n{rag_context}\n\n"
                if rag_context
                else ""
            )
            + "Analyze the source data and produce the structured change analysis."
        )
        logger.info(
            "analyst_agent_start",
            commits=len(commits),
            merge_requests=len(merge_requests),
            issues=len(issues),
        )
        result: ChangeAnalysis = self._llm.invoke(
            [("system", ANALYST_SYSTEM_PROMPT), ("user", user_prompt)]
        )
        logger.info("analyst_agent_done", changes=len(result.changes), themes=result.themes)
        return result
