"""add_cached_recommendations_table

Revision ID: e81ee0a4dbc7
Revises: 5b7ab65a1fe2
Create Date: 2025-09-24 13:31:10.574194

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e81ee0a4dbc7'
down_revision = '5b7ab65a1fe2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create cached_recommendations table
    op.create_table(
        'cached_recommendations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('recommendation_type', sa.String(), nullable=False),
        sa.Column('recommendations_json', sa.String(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_cached_recommendations_user_expires', 'cached_recommendations', ['user_id', 'expires_at'])
    op.create_index('idx_cached_recommendations_expires', 'cached_recommendations', ['expires_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_cached_recommendations_expires', table_name='cached_recommendations')
    op.drop_index('idx_cached_recommendations_user_expires', table_name='cached_recommendations')

    # Drop table
    op.drop_table('cached_recommendations')
