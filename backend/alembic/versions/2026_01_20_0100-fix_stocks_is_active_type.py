"""fix stocks is_active column type

Revision ID: fix_stocks_is_active
Revises: add_fundamental_data
Create Date: 2026-01-20 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_stocks_is_active'
down_revision = 'add_fundamental_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, update all string values to proper boolean format
    # Convert 'True'/'true' to true, everything else to false
    op.execute("""
        UPDATE stocks
        SET is_active = CASE
            WHEN LOWER(is_active::text) IN ('true', 't', '1', 'yes') THEN 'true'
            ELSE 'false'
        END
        WHERE is_active IS NOT NULL
    """)

    # Now alter column type
    op.alter_column('stocks', 'is_active',
                    existing_type=sa.String(),
                    type_=sa.Boolean(),
                    existing_nullable=True,
                    postgresql_using='is_active::boolean')


def downgrade() -> None:
    # Revert to string type if needed
    op.alter_column('stocks', 'is_active',
                    existing_type=sa.Boolean(),
                    type_=sa.String(),
                    existing_nullable=True,
                    postgresql_using="is_active::text")
