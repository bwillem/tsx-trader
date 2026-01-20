#!/usr/bin/env python3
"""
Test fundamental data fetching for a single stock.
This verifies the Alpha Vantage integration and metric calculations.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.models.stock import Stock
from app.models.fundamentals import FundamentalDataQuarterly
from app.services.market_data import AlphaVantageService


def test_fundamental_data(symbol: str = "TD.TO"):
    """Test fundamental data fetching for a stock

    Args:
        symbol: Stock symbol to test (default: TD.TO)
    """
    db = SessionLocal()

    try:
        print(f"=== Testing Fundamental Data for {symbol} ===\n")

        # Get or create stock
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            print(f"Stock {symbol} not found in database. Creating...")
            stock = Stock(
                symbol=symbol,
                name=symbol,
                exchange="TSX",
                is_active=True
            )
            db.add(stock)
            db.flush()

        # Fetch fundamental data
        av_service = AlphaVantageService()
        print(f"Fetching fundamental data from Alpha Vantage...")
        print(f"(This will take ~1 minute due to rate limiting)\n")

        success = av_service.update_fundamental_data_quarterly(db, stock)

        if not success:
            print(f"❌ Failed to fetch fundamental data for {symbol}")
            return

        print(f"\n✓ Successfully fetched fundamental data for {symbol}\n")

        # Query and display the latest fundamental data
        latest = (
            db.query(FundamentalDataQuarterly)
            .filter(FundamentalDataQuarterly.stock_id == stock.id)
            .order_by(FundamentalDataQuarterly.fiscal_date.desc())
            .first()
        )

        if not latest:
            print("No fundamental data found in database")
            return

        print(f"{'='*60}")
        print(f"Latest Quarterly Data (as of {latest.fiscal_date})")
        print(f"{'='*60}\n")

        print(f"MARKET DATA:")
        print(f"  Market Cap:        ${latest.market_cap:,.0f}" if latest.market_cap else "  Market Cap:        N/A")
        print(f"  Enterprise Value:  ${latest.enterprise_value:,.0f}" if latest.enterprise_value else "  Enterprise Value:  N/A")

        print(f"\nBALANCE SHEET:")
        print(f"  Total Assets:      ${latest.total_assets:,.0f}" if latest.total_assets else "  Total Assets:      N/A")
        print(f"  Total Equity:      ${latest.total_equity:,.0f}" if latest.total_equity else "  Total Equity:      N/A")
        print(f"  Total Debt:        ${latest.total_debt:,.0f}" if latest.total_debt else "  Total Debt:        N/A")

        print(f"\nINCOME STATEMENT:")
        print(f"  Revenue:           ${latest.revenue:,.0f}" if latest.revenue else "  Revenue:           N/A")
        print(f"  EBITDA:            ${latest.ebitda:,.0f}" if latest.ebitda else "  EBITDA:            N/A")
        print(f"  Operating Income:  ${latest.operating_income:,.0f}" if latest.operating_income else "  Operating Income:  N/A")
        print(f"  Net Income:        ${latest.net_income:,.0f}" if latest.net_income else "  Net Income:        N/A")

        print(f"\nCASH FLOW:")
        print(f"  Operating Cash:    ${latest.operating_cash_flow:,.0f}" if latest.operating_cash_flow else "  Operating Cash:    N/A")
        print(f"  CapEx:             ${latest.capital_expenditures:,.0f}" if latest.capital_expenditures else "  CapEx:             N/A")
        print(f"  Free Cash Flow:    ${latest.free_cash_flow:,.0f}" if latest.free_cash_flow else "  Free Cash Flow:    N/A")

        print(f"\n{'='*60}")
        print(f"YARTSEVA MULTIBAGGER METRICS")
        print(f"{'='*60}\n")

        print(f"KEY PREDICTORS:")
        if latest.fcf_price_ratio is not None:
            print(f"  FCF/Price:         {latest.fcf_price_ratio:.4f} ({latest.fcf_price_ratio*100:.2f}%) ⭐ STRONGEST")
        else:
            print(f"  FCF/Price:         N/A")

        if latest.book_to_market is not None:
            print(f"  Book/Market:       {latest.book_to_market:.4f}")
            if latest.book_to_market > 0.40:
                print(f"                     ✓ Above 0.40 threshold (value stock)")
            else:
                print(f"                     ⚠ Below 0.40 threshold")
        else:
            print(f"  Book/Market:       N/A")

        print(f"\nPROFITABILITY:")
        print(f"  ROA:               {latest.roa*100:.2f}%" if latest.roa else "  ROA:               N/A")
        print(f"  ROE:               {latest.roe*100:.2f}%" if latest.roe else "  ROE:               N/A")
        print(f"  EBITDA Margin:     {latest.ebitda_margin*100:.2f}%" if latest.ebitda_margin else "  EBITDA Margin:     N/A")
        print(f"  EBIT Margin:       {latest.ebit_margin*100:.2f}%" if latest.ebit_margin else "  EBIT Margin:       N/A")

        print(f"\nGROWTH RATES (YoY):")
        print(f"  Asset Growth:      {latest.asset_growth_rate*100:.2f}%" if latest.asset_growth_rate else "  Asset Growth:      N/A")
        print(f"  EBITDA Growth:     {latest.ebitda_growth_rate*100:.2f}%" if latest.ebitda_growth_rate else "  EBITDA Growth:     N/A")
        print(f"  Revenue Growth:    {latest.revenue_growth_rate*100:.2f}%" if latest.revenue_growth_rate else "  Revenue Growth:    N/A")

        print(f"\nQUALITY FLAGS:")
        print(f"  Profitable:        {'✓ Yes' if latest.is_profitable else '✗ No'}")
        print(f"  Negative Equity:   {'⚠ Yes (AVOID)' if latest.has_negative_equity else '✓ No'}")

        if latest.reinvestment_quality_flag is not None:
            if latest.reinvestment_quality_flag:
                print(f"  Reinvestment:      ✓ Good (Asset growth ≤ EBITDA growth)")
            else:
                print(f"  Reinvestment:      ⚠ Poor (Asset growth > EBITDA growth)")
        else:
            print(f"  Reinvestment:      N/A (need 2+ years of data)")

        print(f"\n{'='*60}\n")

        # Show count of all quarters
        count = db.query(FundamentalDataQuarterly).filter(
            FundamentalDataQuarterly.stock_id == stock.id
        ).count()

        print(f"Total quarters in database: {count}")
        print(f"\nTo view all quarters, query the fundamental_data_quarterly table:")
        print(f"  SELECT fiscal_date, fcf_price_ratio, book_to_market, roa")
        print(f"  FROM fundamental_data_quarterly")
        print(f"  WHERE stock_id = {stock.id}")
        print(f"  ORDER BY fiscal_date DESC;")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "TD.TO"
    test_fundamental_data(symbol)
