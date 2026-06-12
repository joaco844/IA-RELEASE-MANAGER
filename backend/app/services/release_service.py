from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import audit_log
from app.models import Release, ReleaseStatus, User
from app.repositories.releases import ReleaseRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.release import ReleaseGenerateRequest

# Signature of the background workflow runner; injectable for tests.
WorkflowRunner = Callable[..., None]


def _default_runner(*args: object, **kwargs: object) -> None:
    from app.workflows.runner import run_release_workflow

    run_release_workflow(*args, **kwargs)  # type: ignore[arg-type]


class ReleaseService:
    def __init__(self, session: Session, runner: WorkflowRunner | None = None) -> None:
        self.session = session
        self.releases = ReleaseRepository(session)
        self.repos = RepositoryRepository(session)
        self.runner = runner or _default_runner

    def create_release(self, user: User, payload: ReleaseGenerateRequest) -> Release:
        """Create the pending release row. The workflow itself is scheduled by the
        API layer through `schedule_generation` after the transaction commits."""
        repo = self.repos.get_for_owner(payload.repository_id, user.id)
        if repo is None:
            raise NotFoundError("Repository not found")

        r = payload.range
        if r.type == "tag_range":
            range_from, range_to = r.from_tag, r.to_tag
            summary = f"{r.from_tag} → {r.to_tag}"
        elif r.type == "last_days":
            range_from, range_to = str(r.days), None
            summary = f"Last {r.days} days"
        else:
            range_from, range_to = r.since.isoformat() if r.since else None, None
            summary = f"Since {r.since.date().isoformat()}" if r.since else "Since date"

        title = payload.title or (
            f"{repo.name} release — {datetime.now(UTC).date().isoformat()}"
        )
        release = self.releases.add(
            Release(
                repository_id=repo.id,
                title=title,
                status=ReleaseStatus.PENDING.value,
                range_type=r.type,
                range_from=range_from,
                range_to=range_to,
                range_summary=summary,
                slack_channel=payload.slack_channel,
            )
        )
        self.releases.commit()
        audit_log(
            "release_generation_requested",
            user_id=user.id,
            release_id=release.id,
            repository_id=repo.id,
            range=summary,
        )
        return release

    def schedule_generation(self, release: Release, payload: ReleaseGenerateRequest) -> tuple:
        """Return (callable, kwargs) for FastAPI BackgroundTasks."""
        ai = payload.ai
        return self.runner, {
            "release_id": release.id,
            "auto_publish": payload.auto_publish,
            "slack_channel": payload.slack_channel,
            "provider": ai.provider if ai else None,
            "temperature": ai.temperature if ai else None,
        }

    def list_for_user(
        self,
        user: User,
        repository_id: int | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Release], int]:
        return self.releases.list_for_owner(user.id, repository_id, status, page, page_size)

    def get_detail(self, user: User, release_id: int) -> Release:
        release = self.releases.get_for_owner(release_id, user.id)
        if release is None:
            raise NotFoundError("Release not found")
        return release
