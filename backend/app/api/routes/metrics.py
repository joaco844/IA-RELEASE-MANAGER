from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_metrics_service
from app.schemas.metrics import MetricsOut
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])

MetricsSvc = Annotated[MetricsService, Depends(get_metrics_service)]


@router.get("", response_model=MetricsOut)
def get_metrics(user: CurrentUser, service: MetricsSvc) -> MetricsOut:
    return service.compute(user)
