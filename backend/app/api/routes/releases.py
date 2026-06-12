from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status

from app.api.deps import CurrentUser, get_release_service
from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.models import Release
from app.schemas.release import (
    CommitOut,
    IssueOut,
    MergeRequestOut,
    ReleaseDetailOut,
    ReleaseGenerateRequest,
    ReleaseListOut,
    ReleaseMetricsOut,
    ReleaseNotesOut,
    ReleaseOut,
)
from app.services.release_service import ReleaseService

router = APIRouter(prefix="/releases", tags=["releases"])

ReleaseSvc = Annotated[ReleaseService, Depends(get_release_service)]


def _analysis_for_frontend(release: Release) -> dict[str, Any] | None:
    """Regroup the stored flat change list by category for display."""
    if not release.analysis:
        return None
    grouped: dict[str, list[dict[str, Any]]] = {}
    for change in release.analysis.get("changes", []):
        grouped.setdefault(change.get("category", "Other"), []).append(
            {
                "summary": change.get("summary", ""),
                "business_impact": change.get("business_impact", ""),
                "technical_impact": change.get("technical_impact", ""),
                "risk_level": change.get("risk_level", "low"),
                "source_refs": change.get("source_refs", []),
            }
        )
    return {
        "categories": [
            {"category": category, "items": items} for category, items in grouped.items()
        ],
        "overall_risk": release.analysis.get("overall_risk"),
        "themes": release.analysis.get("themes", []),
    }


def _to_detail(release: Release) -> ReleaseDetailOut:
    base = ReleaseOut.model_validate(release)
    return ReleaseDetailOut(
        **base.model_dump(),
        notes=ReleaseNotesOut(
            executive=release.executive_notes,
            technical=release.technical_notes,
            markdown=release.markdown_notes,
            slack=release.slack_notes,
        ),
        qa_report=release.qa_report,
        analysis=_analysis_for_frontend(release),
        themes=release.themes,
        commits=[CommitOut.model_validate(c) for c in release.commits],
        issues=[IssueOut.model_validate(i) for i in release.issues],
        merge_requests=[MergeRequestOut.model_validate(m) for m in release.merge_requests],
        metrics=ReleaseMetricsOut(
            generation_seconds=release.generation_seconds,
            commits_analyzed=release.commits_analyzed,
            issues_analyzed=release.issues_analyzed,
            mrs_analyzed=release.mrs_analyzed,
        ),
    )


@router.post("/generate", response_model=ReleaseOut, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(get_settings().rate_limit_generate)
def generate_release(
    request: Request,
    payload: ReleaseGenerateRequest,
    user: CurrentUser,
    service: ReleaseSvc,
    background_tasks: BackgroundTasks,
) -> ReleaseOut:
    release = service.create_release(user, payload)
    runner, kwargs = service.schedule_generation(release, payload)
    background_tasks.add_task(runner, **kwargs)
    return ReleaseOut.model_validate(release)


@router.get("", response_model=ReleaseListOut)
def list_releases(
    user: CurrentUser,
    service: ReleaseSvc,
    repository_id: int | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ReleaseListOut:
    items, total = service.list_for_user(user, repository_id, status_filter, page, page_size)
    return ReleaseListOut(
        items=[ReleaseOut.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{release_id}", response_model=ReleaseDetailOut)
def get_release(release_id: int, user: CurrentUser, service: ReleaseSvc) -> ReleaseDetailOut:
    return _to_detail(service.get_detail(user, release_id))
