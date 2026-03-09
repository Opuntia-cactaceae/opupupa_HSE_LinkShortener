from typing import Any, Dict

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from ..application.errors.errors import (
    ApplicationError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    LinkExpiredError,
    LinkNotFoundError,
    LinkNotAvailableError,
    ProjectNotFoundError,
    ShortCodeAlreadyExistsError,
    UserNotFoundError,
    UserNotAuthorizedError,
    ValidationError,
)


def map_application_error_to_http(error: ApplicationError) -> HTTPException:
    if isinstance(error, ValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error) or "Validation error",
        )
    if isinstance(error, LinkNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )
    if isinstance(error, LinkExpiredError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link expired",
        )
    if isinstance(error, LinkNotAvailableError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not available",
        )
    if isinstance(error, ShortCodeAlreadyExistsError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Short code already exists",
        )
    if isinstance(error, UserNotAuthorizedError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action",
        )
    if isinstance(error, UserNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if isinstance(error, ProjectNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    if isinstance(error, InvalidCredentialsError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if isinstance(error, EmailAlreadyExistsError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
    )


async def application_error_handler(request: Any, exc: ApplicationError) -> JSONResponse:
    http_exc = map_application_error_to_http(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={"detail": http_exc.detail},
    )