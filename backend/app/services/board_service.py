"""Issue board: live GitLab issues arranged into Open / label lists / Closed columns."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.core.logging import audit_log
from app.core.security import TokenCipher
from app.integrations.gitlab_client import BoardIssueData, LabelData
from app.models import BoardList, Repository, User
from app.repositories.board_lists import BoardListRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.board import (
    BoardColumnOut,
    BoardIssueCreate,
    BoardIssueMove,
    BoardIssueOut,
    BoardLabelOut,
    BoardListCreate,
    BoardListOut,
    BoardOut,
)

_FALLBACK_COLOR = "#6699cc"


class BoardService:
    def __init__(self, session: Session, gitlab_client_factory: Any = None) -> None:
        self.repos = RepositoryRepository(session)
        self.board_lists = BoardListRepository(session)
        self._cipher = TokenCipher()
        # Injectable for tests; defaults to the real client.
        if gitlab_client_factory is None:
            from app.integrations.gitlab_client import GitLabClient

            gitlab_client_factory = GitLabClient
        self._gitlab_factory = gitlab_client_factory

    def get_board(self, user: User, repository_id: int) -> BoardOut:
        repo = self._get_repo(user, repository_id)
        client = self._client(repo)
        labels = client.fetch_labels(repo.project_path)
        issues = client.fetch_board_issues(repo.project_path)
        lists = self.board_lists.list_for_repository(repo.id)

        labels_by_name = {label.name: label for label in labels}
        listed_labels = {board_list.label for board_list in lists}
        open_issues = [i for i in issues if i.state == "opened"]
        closed_issues = [i for i in issues if i.state != "opened"]

        columns = [
            BoardColumnOut(
                key="open",
                title="Open",
                type="open",
                issues=[
                    _issue_out(i)
                    for i in open_issues
                    if not listed_labels.intersection(i.labels)
                ],
            )
        ]
        for board_list in lists:
            columns.append(
                BoardColumnOut(
                    key=f"list:{board_list.id}",
                    title=board_list.label,
                    type="label",
                    list_id=board_list.id,
                    label=_label_out(labels_by_name.get(board_list.label), board_list.label),
                    issues=[_issue_out(i) for i in open_issues if board_list.label in i.labels],
                )
            )
        columns.append(
            BoardColumnOut(
                key="closed",
                title="Closed",
                type="closed",
                issues=[_issue_out(i) for i in closed_issues],
            )
        )

        return BoardOut(
            repository_id=repo.id,
            repository_name=repo.name,
            labels=[_label_out(label, label.name) for label in labels],
            columns=columns,
        )

    def add_list(self, user: User, repository_id: int, payload: BoardListCreate) -> BoardListOut:
        repo = self._get_repo(user, repository_id)
        if self.board_lists.get_by_label(repo.id, payload.label):
            raise ConflictError("A list for this label already exists")

        client = self._client(repo)
        labels = {label.name for label in client.fetch_labels(repo.project_path)}
        if payload.label not in labels:
            raise NotFoundError(f"Label '{payload.label}' does not exist in this project")

        board_list = self.board_lists.add(
            BoardList(
                repository_id=repo.id,
                label=payload.label,
                position=self.board_lists.next_position(repo.id),
            )
        )
        self.board_lists.commit()
        audit_log(
            "board_list_added",
            user_id=user.id,
            repository_id=repo.id,
            label=payload.label,
        )
        return BoardListOut(id=board_list.id, label=board_list.label, position=board_list.position)

    def remove_list(self, user: User, repository_id: int, list_id: int) -> None:
        repo = self._get_repo(user, repository_id)
        board_list = self.board_lists.get_for_repository(list_id, repo.id)
        if board_list is None:
            raise NotFoundError("Board list not found")
        self.board_lists.delete(board_list)
        self.board_lists.commit()
        audit_log(
            "board_list_removed",
            user_id=user.id,
            repository_id=repo.id,
            label=board_list.label,
        )

    def create_issue(
        self, user: User, repository_id: int, payload: BoardIssueCreate
    ) -> BoardIssueOut:
        repo = self._get_repo(user, repository_id)
        client = self._client(repo)
        if payload.labels:
            existing = {label.name for label in client.fetch_labels(repo.project_path)}
            unknown = sorted(set(payload.labels) - existing)
            if unknown:
                raise NotFoundError(
                    f"Labels do not exist in this project: {', '.join(unknown)}"
                )
        issue = client.create_issue(
            repo.project_path, payload.title, payload.description, payload.labels
        )
        audit_log(
            "board_issue_created",
            user_id=user.id,
            repository_id=repo.id,
            issue_iid=issue.iid,
        )
        return _issue_out(issue)

    def move_issue(
        self, user: User, repository_id: int, issue_iid: int, payload: BoardIssueMove
    ) -> BoardIssueOut:
        repo = self._get_repo(user, repository_id)
        src, dst = payload.from_column, payload.to_column
        for ref in (src, dst):
            if ref.type == "label" and not ref.label:
                raise ValidationFailedError("A label column reference requires a label")
        if dst.type == "label" and not self.board_lists.get_by_label(repo.id, dst.label or ""):
            raise NotFoundError(f"No board list exists for label '{dst.label}'")

        # GitLab board semantics: dropping on Closed closes the issue, dragging
        # out of Closed reopens it, label columns add/remove their label.
        state_event = None
        if dst.type == "closed":
            state_event = "close"
        elif src.type == "closed":
            state_event = "reopen"

        client = self._client(repo)
        issue = client.update_board_issue(
            repo.project_path,
            issue_iid,
            add_label=dst.label if dst.type == "label" else None,
            remove_label=src.label if src.type == "label" else None,
            state_event=state_event,
        )
        audit_log(
            "board_issue_moved",
            user_id=user.id,
            repository_id=repo.id,
            issue_iid=issue_iid,
            from_column=src.type,
            to_column=dst.type,
        )
        return _issue_out(issue)

    def _get_repo(self, user: User, repository_id: int) -> Repository:
        repo = self.repos.get_for_owner(repository_id, user.id)
        if repo is None:
            raise NotFoundError("Repository not found")
        return repo

    def _client(self, repo: Repository) -> Any:
        token = self._cipher.decrypt(repo.encrypted_token)
        return self._gitlab_factory(repo.gitlab_url, token)


def _label_out(label: LabelData | None, name: str) -> BoardLabelOut:
    if label is None:
        # The label was deleted in GitLab but the list still exists.
        return BoardLabelOut(name=name, color=_FALLBACK_COLOR, text_color="#ffffff")
    return BoardLabelOut(
        name=label.name,
        color=label.color,
        text_color=label.text_color,
        description=label.description,
    )


def _issue_out(issue: BoardIssueData) -> BoardIssueOut:
    return BoardIssueOut(
        iid=issue.iid,
        title=issue.title,
        state=issue.state,
        labels=issue.labels,
        author_name=issue.author_name,
        assignee_names=issue.assignee_names,
        milestone=issue.milestone,
        created_at=issue.created_at,
        closed_at=issue.closed_at,
        web_url=issue.web_url,
        user_notes_count=issue.user_notes_count,
    )
