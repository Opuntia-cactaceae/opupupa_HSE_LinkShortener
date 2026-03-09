"""allow short code reuse after soft delete

Revision ID: reuse_short_code_after_soft_delete
Revises: add_projects_and_link_fields
Create Date: 2026-03-09 20:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "reuse_short_code"
down_revision = "add_projects_and_link_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_links_short_code", table_name="links")

    op.create_index(
        "uq_links_short_code_active",
        "links",
        ["short_code"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_links_short_code_active", table_name="links")

    op.create_index(
        "ix_links_short_code",
        "links",
        ["short_code"],
        unique=True,
    )