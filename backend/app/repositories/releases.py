from sqlalchemy import func, select

from app.models import Release, ReleaseStatus, Repository
from app.repositories.base import BaseRepository


class ReleaseRepository(BaseRepository[Release]):
    model = Release

    def get_for_owner(self, release_id: int, owner_id: int) -> Release | None:
        return self.session.scalar(
            select(Release)
            .join(Repository)
            .where(Release.id == release_id, Repository.owner_id == owner_id)
        )

    def list_for_owner(
        self,
        owner_id: int,
        repository_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Release], int]:
        query = select(Release).join(Repository).where(Repository.owner_id == owner_id)
        if repository_id is not None:
            query = query.where(Release.repository_id == repository_id)
        if status is not None:
            query = query.where(Release.status == status)

        total = self.session.scalar(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
        items = list(
            self.session.scalars(
                query.order_by(Release.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, int(total or 0)

    def recent_for_repository(self, repository_id: int, limit: int = 10) -> list[Release]:
        return list(
            self.session.scalars(
                select(Release)
                .where(Release.repository_id == repository_id)
                .order_by(Release.created_at.desc())
                .limit(limit)
            )
        )

    def completed_for_owner(self, owner_id: int) -> list[Release]:
        """All successfully generated releases (completed or published) for metrics."""
        return list(
            self.session.scalars(
                select(Release)
                .join(Repository)
                .where(
                    Repository.owner_id == owner_id,
                    Release.status.in_(
                        [ReleaseStatus.COMPLETED.value, ReleaseStatus.PUBLISHED.value]
                    ),
                )
                .order_by(Release.created_at.asc())
            )
        )

    def count_all_for_owner(self, owner_id: int) -> int:
        return int(
            self.session.scalar(
                select(func.count(Release.id))
                .join(Repository)
                .where(Repository.owner_id == owner_id)
            )
            or 0
        )
