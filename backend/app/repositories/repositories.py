from sqlalchemy import select

from app.models import Repository
from app.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository]):
    model = Repository

    def list_for_owner(self, owner_id: int) -> list[Repository]:
        return list(
            self.session.scalars(
                select(Repository)
                .where(Repository.owner_id == owner_id)
                .order_by(Repository.created_at.desc())
            )
        )

    def get_for_owner(self, repository_id: int, owner_id: int) -> Repository | None:
        return self.session.scalar(
            select(Repository).where(
                Repository.id == repository_id, Repository.owner_id == owner_id
            )
        )

    def get_by_path(self, owner_id: int, gitlab_url: str, project_path: str) -> Repository | None:
        return self.session.scalar(
            select(Repository).where(
                Repository.owner_id == owner_id,
                Repository.gitlab_url == gitlab_url,
                Repository.project_path == project_path,
            )
        )
