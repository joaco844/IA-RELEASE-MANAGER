from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Release, User
from app.repositories.releases import ReleaseRepository
from app.schemas.metrics import (
    CategoryCount,
    GenerationTime,
    MetricsOut,
    MetricsTotals,
    WeeklyCount,
)


class MetricsService:
    def __init__(self, session: Session) -> None:
        self.releases = ReleaseRepository(session)

    def compute(self, user: User) -> MetricsOut:
        settings = get_settings()
        completed = self.releases.completed_for_owner(user.id)
        total_releases = self.releases.count_all_for_owner(user.id)

        commits_total = sum(r.commits_analyzed for r in completed)
        issues_total = sum(r.issues_analyzed for r in completed)
        mrs_total = sum(r.mrs_analyzed for r in completed)
        publications = sum(1 for r in completed if r.slack_message_url)

        durations = [r.generation_seconds for r in completed if r.generation_seconds]
        avg_seconds = round(sum(durations) / len(durations), 2) if durations else None

        return MetricsOut(
            totals=MetricsTotals(
                releases=total_releases,
                completed=len(completed),
                commits_analyzed=commits_total,
                issues_analyzed=issues_total,
                mrs_analyzed=mrs_total,
                slack_publications=publications,
                hours_saved=round(len(completed) * settings.hours_saved_per_release, 1),
            ),
            avg_generation_seconds=avg_seconds,
            releases_by_week=self._weekly_counts(completed),
            categories_breakdown=self._category_counts(completed),
            recent_generation_times=[
                GenerationTime(release_id=r.id, title=r.title, seconds=r.generation_seconds)
                for r in completed[-10:]
                if r.generation_seconds
            ],
        )

    @staticmethod
    def _weekly_counts(releases: list[Release]) -> list[WeeklyCount]:
        counter: Counter[str] = Counter()
        for release in releases:
            created: datetime = release.created_at
            year, week, _ = created.isocalendar()
            counter[f"{year}-W{week:02d}"] += 1
        return [WeeklyCount(week=week, count=count) for week, count in sorted(counter.items())]

    @staticmethod
    def _category_counts(releases: list[Release]) -> list[CategoryCount]:
        counter: Counter[str] = Counter()
        for release in releases:
            analysis = release.analysis or {}
            for change in analysis.get("changes", []):
                category = change.get("category")
                if category:
                    counter[category] += 1
        return [
            CategoryCount(category=category, count=count)
            for category, count in counter.most_common()
        ]
