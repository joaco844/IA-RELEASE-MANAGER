"""Domain exceptions mapped to HTTP responses at the API layer."""


class AppError(Exception):
    """Base class for domain errors."""

    status_code: int = 400

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class ExternalServiceError(AppError):
    """A third-party service (GitLab, Slack, LLM provider) failed."""

    status_code = 502


class ValidationFailedError(AppError):
    status_code = 422
