from datetime import datetime
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin, TimestampMixin



class ProjectModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    links: Mapped[list["LinkModel"]] = relationship(
        "LinkModel",
        back_populates="project",
    )