from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_board_service
from app.schemas.board import (
    BoardIssueCreate,
    BoardIssueMove,
    BoardIssueOut,
    BoardListCreate,
    BoardListOut,
    BoardOut,
)
from app.services.board_service import BoardService

router = APIRouter(prefix="/repositories/{repository_id}/board", tags=["issue-board"])

BoardSvc = Annotated[BoardService, Depends(get_board_service)]


@router.get("", response_model=BoardOut)
def get_board(repository_id: int, user: CurrentUser, service: BoardSvc) -> BoardOut:
    return service.get_board(user, repository_id)


@router.post("/lists", response_model=BoardListOut, status_code=status.HTTP_201_CREATED)
def add_board_list(
    repository_id: int, payload: BoardListCreate, user: CurrentUser, service: BoardSvc
) -> BoardListOut:
    return service.add_list(user, repository_id, payload)


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_board_list(
    repository_id: int, list_id: int, user: CurrentUser, service: BoardSvc
) -> None:
    service.remove_list(user, repository_id, list_id)


@router.post("/issues", response_model=BoardIssueOut, status_code=status.HTTP_201_CREATED)
def create_board_issue(
    repository_id: int, payload: BoardIssueCreate, user: CurrentUser, service: BoardSvc
) -> BoardIssueOut:
    return service.create_issue(user, repository_id, payload)


@router.post("/issues/{issue_iid}/move", response_model=BoardIssueOut)
def move_board_issue(
    repository_id: int,
    issue_iid: int,
    payload: BoardIssueMove,
    user: CurrentUser,
    service: BoardSvc,
) -> BoardIssueOut:
    return service.move_issue(user, repository_id, issue_iid, payload)
