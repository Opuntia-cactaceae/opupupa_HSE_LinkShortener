from jose import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from ...application.services.token_provider import TokenProvider
from ..settings import settings


class JwtTokenProvider(TokenProvider):
    def encode(self, user_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.JWT_EXPIRES_MIN)

        payload = {
            "sub": str(user_id),
            "exp": expires_at,
            "iat": now,
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

    def decode(self, token: str) -> Optional[UUID]:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return UUID(payload["sub"])
        except (jwt.JWTError, ValueError, KeyError):
            return None