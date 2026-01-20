-- Migration: Add fundamental data tables
-- Based on: 2026_01_19_2230-add_fundamental_data_tables.py

-- Create fundamental_data_quarterly table
CREATE TABLE IF NOT EXISTS fundamental_data_quarterly (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stocks(id),
    fiscal_date DATE NOT NULL,
    report_date DATE,

    -- Market data
    market_cap FLOAT,
    enterprise_value FLOAT,

    -- Balance sheet metrics
    total_assets FLOAT,
    total_equity FLOAT,
    book_value_per_share FLOAT,
    total_debt FLOAT,
    cash_and_equivalents FLOAT,

    -- Income statement metrics
    revenue FLOAT,
    operating_income FLOAT,
    ebitda FLOAT,
    net_income FLOAT,

    -- Cash flow metrics
    operating_cash_flow FLOAT,
    free_cash_flow FLOAT,
    capital_expenditures FLOAT,

    -- Calculated ratios (Yartseva's key metrics)
    fcf_price_ratio FLOAT,  -- FCF/Price - STRONGEST PREDICTOR
    book_to_market FLOAT,   -- B/M ratio
    roa FLOAT,              -- Return on assets
    roe FLOAT,              -- Return on equity
    ebitda_margin FLOAT,
    ebit_margin FLOAT,

    -- Growth metrics
    asset_growth_rate FLOAT,
    ebitda_growth_rate FLOAT,
    revenue_growth_rate FLOAT,

    -- Quality flags
    has_negative_equity BOOLEAN,
    reinvestment_quality_flag BOOLEAN,
    is_profitable BOOLEAN,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for fundamental_data_quarterly
CREATE INDEX IF NOT EXISTS ix_fundamentals_symbol_date ON fundamental_data_quarterly(stock_id, fiscal_date);
CREATE INDEX IF NOT EXISTS ix_fundamental_data_quarterly_id ON fundamental_data_quarterly(id);
CREATE INDEX IF NOT EXISTS ix_fundamental_data_quarterly_fiscal_date ON fundamental_data_quarterly(fiscal_date);

-- Create fundamental_data_annual table
CREATE TABLE IF NOT EXISTS fundamental_data_annual (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stocks(id),
    fiscal_year INTEGER NOT NULL,

    -- Market data
    market_cap FLOAT,
    enterprise_value FLOAT,

    -- Balance sheet metrics
    total_assets FLOAT,
    total_equity FLOAT,
    book_value_per_share FLOAT,
    total_debt FLOAT,

    -- Income statement metrics
    revenue FLOAT,
    operating_income FLOAT,
    ebitda FLOAT,
    net_income FLOAT,

    -- Cash flow metrics
    operating_cash_flow FLOAT,
    free_cash_flow FLOAT,
    capital_expenditures FLOAT,

    -- Calculated ratios (Yartseva's key metrics)
    fcf_price_ratio FLOAT,
    book_to_market FLOAT,
    roa FLOAT,
    roe FLOAT,
    ebitda_margin FLOAT,
    ebit_margin FLOAT,

    -- Growth metrics
    asset_growth_rate FLOAT,
    ebitda_growth_rate FLOAT,
    revenue_growth_rate FLOAT,

    -- Quality flags
    has_negative_equity BOOLEAN,
    reinvestment_quality_flag BOOLEAN,
    is_profitable BOOLEAN,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for fundamental_data_annual
CREATE INDEX IF NOT EXISTS ix_fundamentals_annual_symbol_year ON fundamental_data_annual(stock_id, fiscal_year);
CREATE INDEX IF NOT EXISTS ix_fundamental_data_annual_id ON fundamental_data_annual(id);
CREATE INDEX IF NOT EXISTS ix_fundamental_data_annual_fiscal_year ON fundamental_data_annual(fiscal_year);

-- Update alembic version table (if it exists)
INSERT INTO alembic_version (version_num)
VALUES ('add_fundamental_data')
ON CONFLICT (version_num) DO NOTHING;

-- Success message
SELECT 'Fundamental data tables created successfully!' AS status;
