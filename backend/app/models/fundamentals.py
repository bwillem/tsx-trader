from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class FundamentalDataQuarterly(Base, TimestampMixin):
    """Quarterly fundamental data for stocks

    Stores key financial metrics used in multibagger screening based on
    Yartseva's "The Alchemy of Multibagger Stocks" research:
    - FCF/Price (free cash flow yield) - strongest predictor
    - Book-to-Market ratio - value factor
    - ROA (return on assets) - profitability factor
    - EBITDA margin - operating efficiency
    - Asset growth vs EBITDA growth - reinvestment quality
    """
    __tablename__ = "fundamental_data_quarterly"
    __table_args__ = (Index("ix_fundamentals_symbol_date", "stock_id", "fiscal_date"),)

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    fiscal_date = Column(Date, nullable=False, index=True)  # End of fiscal quarter
    report_date = Column(Date, nullable=True)  # When data was actually reported

    # Market data (for ratios)
    market_cap = Column(Float, nullable=True)  # Market capitalization
    enterprise_value = Column(Float, nullable=True)  # TEV (Total Enterprise Value)

    # Balance sheet metrics
    total_assets = Column(Float, nullable=True)
    total_equity = Column(Float, nullable=True)  # Book value
    book_value_per_share = Column(Float, nullable=True)
    total_debt = Column(Float, nullable=True)
    cash_and_equivalents = Column(Float, nullable=True)

    # Income statement metrics
    revenue = Column(Float, nullable=True)
    operating_income = Column(Float, nullable=True)  # EBIT
    ebitda = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)

    # Cash flow metrics
    operating_cash_flow = Column(Float, nullable=True)
    free_cash_flow = Column(Float, nullable=True)  # OCF - CapEx
    capital_expenditures = Column(Float, nullable=True)

    # Calculated ratios (Yartseva's key metrics)
    fcf_price_ratio = Column(Float, nullable=True)  # FCF/Price (free cash flow yield) - STRONGEST PREDICTOR
    book_to_market = Column(Float, nullable=True)  # B/M ratio - value factor
    roa = Column(Float, nullable=True)  # Return on assets - profitability
    roe = Column(Float, nullable=True)  # Return on equity
    ebitda_margin = Column(Float, nullable=True)  # EBITDA / Revenue
    ebit_margin = Column(Float, nullable=True)  # Operating margin

    # Growth metrics (for reinvestment quality check)
    asset_growth_rate = Column(Float, nullable=True)  # QoQ or YoY asset growth
    ebitda_growth_rate = Column(Float, nullable=True)  # QoQ or YoY EBITDA growth
    revenue_growth_rate = Column(Float, nullable=True)

    # Quality flags based on Yartseva's findings
    has_negative_equity = Column(Boolean, default=False)  # RED FLAG - avoid these
    reinvestment_quality_flag = Column(Boolean, default=True)  # True if asset_growth <= ebitda_growth
    is_profitable = Column(Boolean, default=False)  # Operating income > 0

    # Relationships
    stock = relationship("Stock", back_populates="fundamental_data")


class FundamentalDataAnnual(Base, TimestampMixin):
    """Annual fundamental data for stocks

    Annual aggregated data for longer-term trend analysis.
    Used for calculating multi-year growth rates and stability metrics.
    """
    __tablename__ = "fundamental_data_annual"
    __table_args__ = (Index("ix_fundamentals_annual_symbol_year", "stock_id", "fiscal_year"),)

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    fiscal_year = Column(Integer, nullable=False, index=True)

    # Same metrics as quarterly but aggregated
    market_cap = Column(Float, nullable=True)
    enterprise_value = Column(Float, nullable=True)

    total_assets = Column(Float, nullable=True)
    total_equity = Column(Float, nullable=True)
    book_value_per_share = Column(Float, nullable=True)
    total_debt = Column(Float, nullable=True)

    revenue = Column(Float, nullable=True)
    operating_income = Column(Float, nullable=True)
    ebitda = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)

    operating_cash_flow = Column(Float, nullable=True)
    free_cash_flow = Column(Float, nullable=True)
    capital_expenditures = Column(Float, nullable=True)

    # Ratios
    fcf_price_ratio = Column(Float, nullable=True)
    book_to_market = Column(Float, nullable=True)
    roa = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    ebitda_margin = Column(Float, nullable=True)
    ebit_margin = Column(Float, nullable=True)

    # Growth rates (YoY)
    asset_growth_rate = Column(Float, nullable=True)
    ebitda_growth_rate = Column(Float, nullable=True)
    revenue_growth_rate = Column(Float, nullable=True)

    # Quality flags
    has_negative_equity = Column(Boolean, default=False)
    reinvestment_quality_flag = Column(Boolean, default=True)
    is_profitable = Column(Boolean, default=False)

    # Relationships
    stock = relationship("Stock", back_populates="fundamental_data_annual")
