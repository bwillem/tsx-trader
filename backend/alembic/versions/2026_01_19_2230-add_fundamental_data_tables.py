"""add fundamental data tables

Revision ID: add_fundamental_data
Revises: initial_schema
Create Date: 2026-01-19 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_fundamental_data'
down_revision = 'initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create fundamental_data_quarterly table
    op.create_table('fundamental_data_quarterly',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('fiscal_date', sa.Date(), nullable=False),
    sa.Column('report_date', sa.Date(), nullable=True),
    # Market data
    sa.Column('market_cap', sa.Float(), nullable=True),
    sa.Column('enterprise_value', sa.Float(), nullable=True),
    # Balance sheet metrics
    sa.Column('total_assets', sa.Float(), nullable=True),
    sa.Column('total_equity', sa.Float(), nullable=True),
    sa.Column('book_value_per_share', sa.Float(), nullable=True),
    sa.Column('total_debt', sa.Float(), nullable=True),
    sa.Column('cash_and_equivalents', sa.Float(), nullable=True),
    # Income statement metrics
    sa.Column('revenue', sa.Float(), nullable=True),
    sa.Column('operating_income', sa.Float(), nullable=True),
    sa.Column('ebitda', sa.Float(), nullable=True),
    sa.Column('net_income', sa.Float(), nullable=True),
    # Cash flow metrics
    sa.Column('operating_cash_flow', sa.Float(), nullable=True),
    sa.Column('free_cash_flow', sa.Float(), nullable=True),
    sa.Column('capital_expenditures', sa.Float(), nullable=True),
    # Calculated ratios (Yartseva's key metrics)
    sa.Column('fcf_price_ratio', sa.Float(), nullable=True),  # FCF/Price - STRONGEST PREDICTOR
    sa.Column('book_to_market', sa.Float(), nullable=True),  # B/M ratio
    sa.Column('roa', sa.Float(), nullable=True),  # Return on assets
    sa.Column('roe', sa.Float(), nullable=True),  # Return on equity
    sa.Column('ebitda_margin', sa.Float(), nullable=True),
    sa.Column('ebit_margin', sa.Float(), nullable=True),
    # Growth metrics
    sa.Column('asset_growth_rate', sa.Float(), nullable=True),
    sa.Column('ebitda_growth_rate', sa.Float(), nullable=True),
    sa.Column('revenue_growth_rate', sa.Float(), nullable=True),
    # Quality flags
    sa.Column('has_negative_equity', sa.Boolean(), nullable=True),
    sa.Column('reinvestment_quality_flag', sa.Boolean(), nullable=True),
    sa.Column('is_profitable', sa.Boolean(), nullable=True),
    # Timestamps
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fundamentals_symbol_date', 'fundamental_data_quarterly', ['stock_id', 'fiscal_date'], unique=False)
    op.create_index(op.f('ix_fundamental_data_quarterly_id'), 'fundamental_data_quarterly', ['id'], unique=False)
    op.create_index(op.f('ix_fundamental_data_quarterly_fiscal_date'), 'fundamental_data_quarterly', ['fiscal_date'], unique=False)

    # Create fundamental_data_annual table
    op.create_table('fundamental_data_annual',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('fiscal_year', sa.Integer(), nullable=False),
    # Market data
    sa.Column('market_cap', sa.Float(), nullable=True),
    sa.Column('enterprise_value', sa.Float(), nullable=True),
    # Balance sheet metrics
    sa.Column('total_assets', sa.Float(), nullable=True),
    sa.Column('total_equity', sa.Float(), nullable=True),
    sa.Column('book_value_per_share', sa.Float(), nullable=True),
    sa.Column('total_debt', sa.Float(), nullable=True),
    # Income statement metrics
    sa.Column('revenue', sa.Float(), nullable=True),
    sa.Column('operating_income', sa.Float(), nullable=True),
    sa.Column('ebitda', sa.Float(), nullable=True),
    sa.Column('net_income', sa.Float(), nullable=True),
    # Cash flow metrics
    sa.Column('operating_cash_flow', sa.Float(), nullable=True),
    sa.Column('free_cash_flow', sa.Float(), nullable=True),
    sa.Column('capital_expenditures', sa.Float(), nullable=True),
    # Calculated ratios (Yartseva's key metrics)
    sa.Column('fcf_price_ratio', sa.Float(), nullable=True),
    sa.Column('book_to_market', sa.Float(), nullable=True),
    sa.Column('roa', sa.Float(), nullable=True),
    sa.Column('roe', sa.Float(), nullable=True),
    sa.Column('ebitda_margin', sa.Float(), nullable=True),
    sa.Column('ebit_margin', sa.Float(), nullable=True),
    # Growth metrics
    sa.Column('asset_growth_rate', sa.Float(), nullable=True),
    sa.Column('ebitda_growth_rate', sa.Float(), nullable=True),
    sa.Column('revenue_growth_rate', sa.Float(), nullable=True),
    # Quality flags
    sa.Column('has_negative_equity', sa.Boolean(), nullable=True),
    sa.Column('reinvestment_quality_flag', sa.Boolean(), nullable=True),
    sa.Column('is_profitable', sa.Boolean(), nullable=True),
    # Timestamps
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fundamentals_annual_symbol_year', 'fundamental_data_annual', ['stock_id', 'fiscal_year'], unique=False)
    op.create_index(op.f('ix_fundamental_data_annual_id'), 'fundamental_data_annual', ['id'], unique=False)
    op.create_index(op.f('ix_fundamental_data_annual_fiscal_year'), 'fundamental_data_annual', ['fiscal_year'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fundamental_data_annual_fiscal_year'), table_name='fundamental_data_annual')
    op.drop_index(op.f('ix_fundamental_data_annual_id'), table_name='fundamental_data_annual')
    op.drop_index('ix_fundamentals_annual_symbol_year', table_name='fundamental_data_annual')
    op.drop_table('fundamental_data_annual')

    op.drop_index(op.f('ix_fundamental_data_quarterly_fiscal_date'), table_name='fundamental_data_quarterly')
    op.drop_index(op.f('ix_fundamental_data_quarterly_id'), table_name='fundamental_data_quarterly')
    op.drop_index('ix_fundamentals_symbol_date', table_name='fundamental_data_quarterly')
    op.drop_table('fundamental_data_quarterly')
