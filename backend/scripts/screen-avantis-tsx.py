#!/usr/bin/env python3
"""
Screen TSX stocks using Avantis Investors' methodology

This creates a diversified small cap value portfolio suitable for
core holdings, using factor-based screening:
- Value: Book-to-Price ratio
- Profitability: Cash from Operations / Book Equity
- Size: Small cap tilt ($300M-$2B)
- Quality: Profitability + reinvestment screens

Usage:
    python scripts/screen-avantis-tsx.py [num_stocks]
    python scripts/screen-avantis-tsx.py 20        # Screen for top 20 stocks
    python scripts/screen-avantis-tsx.py portfolio # Show portfolio weights
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_context
from app.services.screening.avantis_tsx_screener import AvantisTSXScreener


def main():
    """Run Avantis-style TSX screening"""

    # Parse arguments
    limit = 20
    show_portfolio = False

    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'portfolio':
            show_portfolio = True
            limit = 20
        else:
            try:
                limit = int(sys.argv[1])
            except ValueError:
                print(f"Invalid argument: {sys.argv[1]}")
                print("Usage: python screen-avantis-tsx.py [num_stocks|portfolio]")
                return

    # Initialize screener with Avantis-style parameters
    screener = AvantisTSXScreener(
        min_book_to_price=0.40,  # Value factor
        min_cash_profitability=0.10,  # 10% cash ROE minimum
        min_market_cap=300_000_000,  # $300M
        max_market_cap=2_000_000_000,  # $2B
        include_fcf_filter=True,  # Add FCF/Price quality screen
        min_fcf_price_ratio=0.03,  # 3% FCF yield minimum
    )

    with get_db_context() as db:
        print("=" * 80)
        print("AVANTIS-STYLE TSX SCREENING")
        print("=" * 80)
        print()

        # Get statistics
        stats = screener.get_statistics(db)

        print("📊 SCREENING STATISTICS")
        print(f"Total stocks with fundamental data: {stats['total_stocks_with_fundamentals']}")
        print(f"Passing all filters: {stats['passing_all_filters']} ({stats['pass_rate']:.1%})")
        print()
        print("Filter thresholds:")
        print(f"  • Book-to-Price: ≥ {stats['filters']['min_book_to_price']:.2f}")
        print(f"  • Cash Profitability: ≥ {stats['filters']['min_cash_profitability']:.1%}")
        print(f"  • Market Cap: {stats['filters']['market_cap_range']}")
        if stats['filters']['fcf_filter_enabled']:
            print(f"  • FCF/Price: ≥ {stats['filters']['min_fcf_price_ratio']:.1%}")
        print()

        if stats['passing_all_filters'] > 0:
            print("Average metrics (passing stocks):")
            print(f"  • Book-to-Price: {stats['avg_book_to_price']:.3f}")
            print(f"  • Cash Profitability: {stats['avg_cash_profitability']:.2%}")
            print(f"  • FCF/Price: {stats['avg_fcf_price_ratio']:.2%}")
            print(f"  • Factor Score: {stats['avg_factor_score']:.1f}/100")

        print()
        print("=" * 80)

        # Get candidates
        candidates = screener.get_candidates(db, limit=limit)

        if not candidates:
            print()
            print("❌ No stocks passed all filters.")
            print()
            print("Suggestions:")
            print("  1. Lower the thresholds (min_book_to_price, min_cash_profitability)")
            print("  2. Wait for weekly fundamental data update to run")
            print("  3. Expand market cap range")
            return

        print()
        print(f"🎯 TOP {len(candidates)} AVANTIS-STYLE CANDIDATES")
        print()

        # Show portfolio or detailed results
        if show_portfolio:
            # Get portfolio weights
            portfolio = screener.get_portfolio_weights(db, num_holdings=20, weighting_method="equal")

            print("PORTFOLIO ALLOCATION (Equal Weight)")
            print()

            for i, (stock, weight) in enumerate(portfolio, 1):
                # Find the candidate for this stock
                candidate = next(c for c in candidates if c.stock_id == stock.id)

                print(f"{i}. {candidate.symbol} - {candidate.name}")
                print(f"   Weight: {weight:.2%}")
                print(f"   Sector: {candidate.sector}")
                print(f"   Factor Score: {candidate.factor_score:.1f}/100")
                print(f"   Book/Price: {candidate.book_to_price:.3f} | Cash Prof: {candidate.cash_profitability:.2%}")
                if candidate.fcf_price_ratio:
                    print(f"   FCF/Price: {candidate.fcf_price_ratio:.2%}")
                print()
        else:
            # Show detailed results
            for i, candidate in enumerate(candidates, 1):
                print(f"{i}. {candidate.symbol} - {candidate.name}")
                print(f"   Sector: {candidate.sector}")
                print(f"   FACTOR SCORE: {candidate.factor_score:.1f}/100")
                print()

                print("   AVANTIS CORE FACTORS:")
                print(f"     Book-to-Price:      {candidate.book_to_price:.3f}")
                print(f"     Cash Profitability: {candidate.cash_profitability:.2%} (OCF / Book Equity)")
                print()

                print("   SIZE & VALUATION:")
                print(f"     Market Cap:         ${candidate.market_cap:,.0f}")
                if candidate.fcf_price_ratio:
                    print(f"     FCF/Price:          {candidate.fcf_price_ratio:.2%}")
                print()

                print("   QUALITY METRICS:")
                if candidate.roa:
                    print(f"     ROA:                {candidate.roa:.2%}")
                if candidate.roe:
                    print(f"     ROE:                {candidate.roe:.2%}")
                print(f"     Profitable:         {'✓ Yes' if candidate.is_profitable else '✗ No'}")
                print(f"     Reinvestment Quality: {'✓ Good' if candidate.reinvestment_quality_flag else '✗ Poor'}")
                print()

        print("=" * 80)
        print()
        print("💡 INTERPRETATION:")
        print()
        print("This is an AVANTIS-STYLE factor portfolio for TSX stocks:")
        print("  • Suitable for CORE HOLDINGS (60-70% of portfolio)")
        print("  • Diversified across 15-25 stocks")
        print("  • Rebalance quarterly or semi-annually")
        print("  • Lower risk than concentrated multibagger approach")
        print()
        print("For HIGH-CONVICTION satellite holdings, use:")
        print("  python scripts/screen-multibaggers.py 10")
        print()


if __name__ == "__main__":
    main()
