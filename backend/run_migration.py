#!/usr/bin/env python3
"""
Run database migration to create fundamental data tables
"""

import sys

# Try to import psycopg2
try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed")
    print("Install with: pip install psycopg2-binary")
    sys.exit(1)

# Database connection string
DATABASE_URL = "postgresql://neondb_owner:npg_9UQMpzZf7Pmy@ep-rapid-star-ahch70oz-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

# SQL for creating fundamental data tables
SQL = """
-- Create fundamental_data_quarterly table
CREATE TABLE IF NOT EXISTS fundamental_data_quarterly (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stocks(id),
    fiscal_date DATE NOT NULL,
    report_date DATE,
    market_cap FLOAT,
    enterprise_value FLOAT,
    total_assets FLOAT,
    total_equity FLOAT,
    book_value_per_share FLOAT,
    total_debt FLOAT,
    cash_and_equivalents FLOAT,
    revenue FLOAT,
    operating_income FLOAT,
    ebitda FLOAT,
    net_income FLOAT,
    operating_cash_flow FLOAT,
    free_cash_flow FLOAT,
    capital_expenditures FLOAT,
    fcf_price_ratio FLOAT,
    book_to_market FLOAT,
    roa FLOAT,
    roe FLOAT,
    ebitda_margin FLOAT,
    ebit_margin FLOAT,
    asset_growth_rate FLOAT,
    ebitda_growth_rate FLOAT,
    revenue_growth_rate FLOAT,
    has_negative_equity BOOLEAN,
    reinvestment_quality_flag BOOLEAN,
    is_profitable BOOLEAN,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_fundamentals_symbol_date ON fundamental_data_quarterly(stock_id, fiscal_date);
CREATE INDEX IF NOT EXISTS ix_fundamental_data_quarterly_id ON fundamental_data_quarterly(id);
CREATE INDEX IF NOT EXISTS ix_fundamental_data_quarterly_fiscal_date ON fundamental_data_quarterly(fiscal_date);

-- Create fundamental_data_annual table
CREATE TABLE IF NOT EXISTS fundamental_data_annual (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stocks(id),
    fiscal_year INTEGER NOT NULL,
    market_cap FLOAT,
    enterprise_value FLOAT,
    total_assets FLOAT,
    total_equity FLOAT,
    book_value_per_share FLOAT,
    total_debt FLOAT,
    revenue FLOAT,
    operating_income FLOAT,
    ebitda FLOAT,
    net_income FLOAT,
    operating_cash_flow FLOAT,
    free_cash_flow FLOAT,
    capital_expenditures FLOAT,
    fcf_price_ratio FLOAT,
    book_to_market FLOAT,
    roa FLOAT,
    roe FLOAT,
    ebitda_margin FLOAT,
    ebit_margin FLOAT,
    asset_growth_rate FLOAT,
    ebitda_growth_rate FLOAT,
    revenue_growth_rate FLOAT,
    has_negative_equity BOOLEAN,
    reinvestment_quality_flag BOOLEAN,
    is_profitable BOOLEAN,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_fundamentals_annual_symbol_year ON fundamental_data_annual(stock_id, fiscal_year);
CREATE INDEX IF NOT EXISTS ix_fundamental_data_annual_id ON fundamental_data_annual(id);
CREATE INDEX IF NOT EXISTS ix_fundamental_data_annual_fiscal_year ON fundamental_data_annual(fiscal_year);

-- Update alembic version
INSERT INTO alembic_version (version_num)
VALUES ('add_fundamental_data')
ON CONFLICT (version_num) DO NOTHING;
"""

def run_migration():
    """Run the migration"""
    print("Connecting to database...")

    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Running migration...")

        # Execute SQL
        cursor.execute(SQL)

        print("✓ Migration completed successfully!")
        print("\nCreated tables:")
        print("  - fundamental_data_quarterly")
        print("  - fundamental_data_annual")
        print("\nNext steps:")
        print("  1. Fetch fundamental data: python scripts/test-fundamentals.py TD.TO")
        print("  2. Run multibagger screening: python scripts/screen-multibaggers.py")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
