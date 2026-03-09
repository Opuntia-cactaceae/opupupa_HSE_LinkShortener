from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LinkStatsModel(Base):
    __tablename__ = "link_stats"

    link_id: Mapped[UUID] = mapped_column(
        ForeignKey("links.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    clicks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )