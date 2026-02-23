"""Add step and details to job_logs for workflow logs

Revision ID: b1c66b222210
Revises: aec55a121109
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b1c66b222210"
down_revision: Union[str, Sequence[str], None] = "aec55a121109"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("job_logs", sa.Column("step", sa.String(length=100), nullable=True))
    op.add_column("job_logs", sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("job_logs", "details")
    op.drop_column("job_logs", "step")
