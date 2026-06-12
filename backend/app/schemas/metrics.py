from pydantic import BaseModel


class MetricsTotals(BaseModel):
    releases: int
    completed: int
    commits_analyzed: int
    issues_analyzed: int
    mrs_analyzed: int
    slack_publications: int
    hours_saved: float


class WeeklyCount(BaseModel):
    week: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class GenerationTime(BaseModel):
    release_id: int
    title: str
    seconds: float


class MetricsOut(BaseModel):
    totals: MetricsTotals
    avg_generation_seconds: float | None
    releases_by_week: list[WeeklyCount]
    categories_breakdown: list[CategoryCount]
    recent_generation_times: list[GenerationTime]
