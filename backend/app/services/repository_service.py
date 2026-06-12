from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import audit_log
from app.core.security import TokenCipher
from app.models import Repository, User
from app.repositories.releases import ReleaseRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.repository import RepositoryConnect


class RepositoryService:
    def __init__(self, session: Session, gitlab_client_factory: Any = None) -> None:
        self.repos = RepositoryRepository(session)
        self.releases = ReleaseRepository(session)
        self._cipher = TokenCipher()
        # Injectable for tests; defaults to the real client.
        if gitlab_client_factory is None:
            from app.integrations.gitlab_client import GitLabClient

            gitlab_client_factory = GitLabClient
        self._gitlab_factory = gitlab_client_factory

    def connect(self, user: User, payload: RepositoryConnect) -> Repository:
        gitlab_url = payload.gitlab_url.rstrip("/")
        if self.repos.get_by_path(user.id, gitlab_url, payload.project_path):
            raise ConflictError("This repository is already connected")

        # Validate credentials and fetch metadata before persisting anything.
        client = self._gitlab_factory(gitlab_url, payload.access_token)
        info = client.verify_project(payload.project_path)

        repository = self.repos.add(
            Repository(
                owner_id=user.id,
                name=payload.name or info.name,
                gitlab_url=gitlab_url,
                project_path=info.path_with_namespace,
                gitlab_project_id=info.id,
                default_branch=info.default_branch,
                description=info.description,
                encrypted_token=self._cipher.encrypt(payload.access_token),
            )
        )
        self.repos.commit()
        audit_log("repository_connected", user_id=user.id, repository_id=repository.id)
        return repository

    def list_for_user(self, user: User) -> list[dict[str, Any]]:
        result = []
        for repo in self.repos.list_for_owner(user.id):
            recent = self.releases.recent_for_repository(repo.id, limit=1)
            result.append(self._to_dict(repo, recent[0].created_at if recent else None))
        return result

    def get_detail(self, user: User, repository_id: int) -> tuple[Repository, list]:
        repo = self.repos.get_for_owner(repository_id, user.id)
        if repo is None:
            raise NotFoundError("Repository not found")
        recent = self.releases.recent_for_repository(repo.id, limit=10)
        return repo, recent

    def delete(self, user: User, repository_id: int) -> None:
        repo = self.repos.get_for_owner(repository_id, user.id)
        if repo is None:
            raise NotFoundError("Repository not found")
        self.repos.delete(repo)
        self.repos.commit()
        audit_log("repository_deleted", user_id=user.id, repository_id=repository_id)

    @staticmethod
    def _to_dict(repo: Repository, last_release_at: Any) -> dict[str, Any]:
        return {
            "id": repo.id,
            "name": repo.name,
            "gitlab_url": repo.gitlab_url,
            "project_path": repo.project_path,
            "default_branch": repo.default_branch,
            "description": repo.description,
            "last_release_at": last_release_at,
            "created_at": repo.created_at,
        }
