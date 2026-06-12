from sqlalchemy import select

from app.models import SlackWorkspace
from app.repositories.base import BaseRepository


class SlackWorkspaceRepository(BaseRepository[SlackWorkspace]):
    model = SlackWorkspace

    def get_for_owner(self, owner_id: int) -> SlackWorkspace | None:
        return self.session.scalar(
            select(SlackWorkspace).where(SlackWorkspace.owner_id == owner_id)
        )
