"""Add unified_schema_versions table for Schema Fusion Engine

Revision ID: c2d77c333321
Revises: b1c66b222210
Create Date: 2025-02-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'c2d77c333321'
down_revision = 'b1c66b222210'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'unified_schema_versions',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('job_id', UUID(as_uuid=False), sa.ForeignKey('jobs.id')),
        sa.Column('schema_json', JSONB, nullable=False),
        sa.Column('sources', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('unified_schema_versions')
