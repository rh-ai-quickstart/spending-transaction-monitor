"""merge all heads - final integration

Revision ID: merge_all_heads_final
Revises: c2241f95e582, eb7dc605eb0f
Create Date: 2025-09-26 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_all_heads_final'
down_revision = ('c2241f95e582', 'eb7dc605eb0f')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
