"""Add details column to lineage for field-level lineage and fallbacks

Revision ID: d3e88d444432
Revises: c2d77c333321
Create Date: 2025-02-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'd3e88d444432'
down_revision = 'c2d77c333321'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('lineage', sa.Column('details', JSONB))


def downgrade():
    op.drop_column('lineage', 'details')
