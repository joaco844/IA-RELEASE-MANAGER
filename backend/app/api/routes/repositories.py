from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_repository_service
from app.schemas.release import ReleaseOut
from app.schemas.repository import RepositoryConnect, RepositoryDetailOut, RepositoryOut
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])

RepoSvc = Annotated[RepositoryService, Depends(get_repository_service)]


@router.post("/connect", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
def connect_repository(
    payload: RepositoryConnect, user: CurrentUser, service: RepoSvc
) -> RepositoryOut:
    return RepositoryOut.model_validate(service.connect(user, payload))


@router.get("", response_model=list[RepositoryOut])
def list_repositories(user: CurrentUser, service: RepoSvc) -> list[RepositoryOut]:
    return [RepositoryOut.model_validate(item) for item in service.list_for_user(user)]


@router.get("/{repository_id}", response_model=RepositoryDetailOut)
def get_repository(
    repository_id: int, user: CurrentUser, service: RepoSvc
) -> RepositoryDetailOut:
    repo, recent = service.get_detail(user, repository_id)
    detail = RepositoryDetailOut.model_validate(repo)
    detail.last_release_at = recent[0].created_at if recent else None
    detail.recent_releases = [ReleaseOut.model_validate(r) for r in recent]
    return detail


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(repository_id: int, user: CurrentUser, service: RepoSvc) -> None:
    service.delete(user, repository_id)
