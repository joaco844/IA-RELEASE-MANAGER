from sqlalchemy import func, select

from app.models import BoardList
from app.repositories.base import BaseRepository


class BoardListRepository(BaseRepository[BoardList]):
    model = BoardList

    def list_for_repository(self, repository_id: int) -> list[BoardList]:
        return list(
            self.session.scalars(
                select(BoardList)
                .where(BoardList.repository_id == repository_id)
                .order_by(BoardList.position, BoardList.id)
            )
        )

    def get_by_label(self, repository_id: int, label: str) -> BoardList | None:
        return self.session.scalar(
            select(BoardList).where(
                BoardList.repository_id == repository_id, BoardList.label == label
            )
        )

    def get_for_repository(self, list_id: int, repository_id: int) -> BoardList | None:
        return self.session.scalar(
            select(BoardList).where(
                BoardList.id == list_id, BoardList.repository_id == repository_id
            )
        )

    def next_position(self, repository_id: int) -> int:
        current = self.session.scalar(
            select(func.max(BoardList.position)).where(BoardList.repository_id == repository_id)
        )
        return (current + 1) if current is not None else 0
