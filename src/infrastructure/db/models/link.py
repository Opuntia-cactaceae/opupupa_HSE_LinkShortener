from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin, TimestampMixin


class LinkModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "links"
    __table_args__ = (
        Index(
            "uq_links_short_code_active",
            "short_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    short_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    original_url: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    owner_user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    expired_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    project: Mapped[Optional["ProjectModel"]] = relationship(
        "ProjectModel",
        back_populates="links",
    )