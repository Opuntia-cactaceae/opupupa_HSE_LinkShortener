"""add projects table and link fields

Revision ID: add_projects_and_link_fields
Revises: initial
Create Date: 2026-03-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'add_projects_and_link_fields'
down_revision = 'initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column(
            'owner_user_id',
            UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.add_column(
        'links',
        sa.Column(
            'project_id',
            UUID(as_uuid=True),
            sa.ForeignKey('projects.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
    )

    op.add_column('links', sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('links', 'expired_at')
    op.drop_column('links', 'project_id')
    op.drop_table('projects')