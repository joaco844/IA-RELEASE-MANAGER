"""RAG layer: per-repository knowledge base over issues, merge requests,
commit messages and previous release notes.

Documents are embedded with the configured provider's embedding model and
stored in a persistent Chroma collection. Before generating release notes the
workflow retrieves the most relevant historical context.
"""

from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.gitlab_client import (
    CommitData,
    IssueData,
    MergeRequestData,
    PreviousRelease,
)

if TYPE_CHECKING:
    from langchain_core.documents import Document

logger = get_logger(__name__)


def build_documents(
    commits: list[CommitData],
    merge_requests: list[MergeRequestData],
    issues: list[IssueData],
    previous_releases: list[PreviousRelease],
) -> list["Document"]:
    from langchain_core.documents import Document

    docs: list[Document] = []
    for c in commits:
        text = f"Commit {c.sha[:8]}: {c.title}\n{(c.message or '')[:1000]}"
        docs.append(
            Document(
                page_content=text,
                metadata={"source_type": "commit", "ref": f"commit:{c.sha[:8]}"},
            )
        )
    for mr in merge_requests:
        text = f"Merge request !{mr.iid}: {mr.title}\n{(mr.description or '')[:1500]}"
        docs.append(
            Document(
                page_content=text,
                metadata={"source_type": "merge_request", "ref": f"mr:!{mr.iid}"},
            )
        )
    for issue in issues:
        text = f"Issue #{issue.iid}: {issue.title}\n{(issue.description or '')[:1500]}"
        docs.append(
            Document(
                page_content=text,
                metadata={"source_type": "issue", "ref": f"issue:#{issue.iid}"},
            )
        )
    for rel in previous_releases:
        text = (
            f"Previous release {rel.tag_name}"
            + (f" ({rel.name})" if rel.name else "")
            + f":\n{(rel.description or '')[:3000]}"
        )
        docs.append(
            Document(
                page_content=text,
                metadata={"source_type": "release_notes", "ref": f"release:{rel.tag_name}"},
            )
        )
    return docs


class ReleaseKnowledgeBase:
    """Persistent vector store scoped to one repository."""

    def __init__(self, repository_id: int, provider: str | None = None) -> None:
        from langchain_chroma import Chroma

        from app.ai.provider import get_embeddings

        settings = get_settings()
        self._store = Chroma(
            collection_name=f"repository_{repository_id}",
            embedding_function=get_embeddings(provider),
            persist_directory=settings.rag_persist_dir,
        )

    def index(self, documents: list["Document"]) -> int:
        if not documents:
            return 0
        # Deterministic ids let re-indexing the same refs upsert instead of duplicate.
        ids = [
            f"{doc.metadata.get('source_type', 'doc')}-{doc.metadata.get('ref', i)}"
            for i, doc in enumerate(documents)
        ]
        self._store.add_documents(documents=documents, ids=ids)
        logger.info("rag_indexed", count=len(documents))
        return len(documents)

    def retrieve(self, query: str, k: int | None = None) -> list["Document"]:
        settings = get_settings()
        return self._store.similarity_search(query, k=k or settings.rag_top_k)

    def retrieve_context(self, query: str, k: int | None = None) -> str:
        """Retrieve and format historical context for prompt injection."""
        try:
            docs = self.retrieve(query, k)
        except Exception as exc:  # noqa: BLE001 - RAG is enhancement, not critical path
            logger.warning("rag_retrieval_failed", error=str(exc))
            return ""
        if not docs:
            return ""
        sections: list[str] = []
        for doc in docs:
            ref = doc.metadata.get("ref", "unknown")
            sections.append(f"[{ref}]\n{doc.page_content}")
        return "\n\n".join(sections)


def index_release_notes(
    kb: "ReleaseKnowledgeBase", release_title: str, markdown_notes: str
) -> None:
    """Store final notes back into the KB so future releases can reference them."""
    from langchain_core.documents import Document

    try:
        kb.index(
            [
                Document(
                    page_content=f"Release notes '{release_title}':\n{markdown_notes[:4000]}",
                    metadata={"source_type": "release_notes", "ref": f"generated:{release_title}"},
                )
            ]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("rag_release_notes_index_failed", error=str(exc))


def make_knowledge_base(repository_id: int, provider: str | None = None) -> Any:
    """Factory that degrades gracefully when RAG is disabled or unavailable."""
    settings = get_settings()
    if not settings.rag_enabled:
        return None
    try:
        return ReleaseKnowledgeBase(repository_id, provider)
    except Exception as exc:  # noqa: BLE001 - missing chroma/keys should not break generation
        logger.warning("rag_unavailable", error=str(exc))
        return None
