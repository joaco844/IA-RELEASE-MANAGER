from app.models import GenerationLog
from app.repositories.base import BaseRepository


class GenerationLogRepository(BaseRepository[GenerationLog]):
    model = GenerationLog
