#!/usr/bin/env python3
"""
Compare Avantis-style vs Multibagger screening strategies

Shows the difference between:
1. Avantis TSX: Diversified factor portfolio (core holdings)
2. Multibagger: Concentrated high-conviction picks (satellite holdings)

Usage:
    python scripts/compare-strategies.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_context
from app.services.screening.avantis_tsx_screener import AvantisTSXScreener
from app.services.screening.multibagger_screener import MultibaggerScreener


def main():
    """Compare both screening approaches"""

    # Initialize both screeners
    avantis = AvantisTSXScreener(
        min_book_to_price=0.40,
        min_cash_profitability=0.10,
        include_fcf_filter=True,
        min_fcf_price_ratio=0.03,  # Lower threshold (3%)
    )

    multibagger = MultibaggerScreener(
        min_fcf_price_ratio=0.05,  # Higher threshold (5%)
        min_book_to_market=0.40,
        min_market_cap=300_000_000,
        max_market_cap=2_000_000_000,
    )

    with get_db_context() as db:
        print("=" * 100)
        print("STRATEGY COMPARISON: Avantis TSX vs Multibagger")
        print("=" * 100)
        print()

        # Get results from both
        avantis_candidates = avantis.get_candidates(db, limit=20)
        multibagger_results = multibagger.screen(db, limit=10)
        multibagger_symbols = {stock.symbol for stock, _, _ in multibagger_results}

        print("📊 OVERVIEW")
        print()
        print(f"{'Strategy':<30} {'Holdings':<12} {'Philosophy':<50}")
        print("-" * 100)
        print(f"{'Avantis TSX (Core)':<30} {'15-25':<12} {'Diversified factor exposure (Value + Profitability)'}")
        print(f"{'Multibagger (Satellite)':<30} {'5-10':<12} {'Concentrated bets on 10x potential (FCF + Timing)'}")
        print()

        # Statistics comparison
        avantis_stats = avantis.get_statistics(db)
        multibagger_stats = multibagger.get_screening_stats(db)

        print("=" * 100)
        print("SCREENING STATISTICS")
        print("=" * 100)
        print()

        print(f"{'Metric':<40} {'Avantis TSX':<30} {'Multibagger':<30}")
        print("-" * 100)
        print(f"{'Stocks passing filters':<40} {avantis_stats['passing_all_filters']:<30} {multibagger_stats['passing_all_filters']:<30}")
        print(f"{'Pass rate':<40} {avantis_stats['pass_rate']:.1%:<30} {multibagger_stats['passing_all_filters'] / multibagger_stats['total_stocks_with_fundamentals']:.1%:<30}")
        print()

        print(f"{'Average Book-to-Market':<40} {avantis_stats['avg_book_to_price']:.3f:<30} {multibagger_stats['avg_book_to_market']:.3f:<30}")
        print(f"{'Average FCF/Price':<40} {avantis_stats['avg_fcf_price_ratio']:.2%:<30} {multibagger_stats['avg_fcf_price_ratio']:.2%:<30}")
        print(f"{'Average Cash Profitability':<40} {avantis_stats['avg_cash_profitability']:.2%:<30} {'N/A':<30}")
        print()

        print("=" * 100)
        print("FILTER DIFFERENCES")
        print("=" * 100)
        print()

        print(f"{'Filter':<40} {'Avantis TSX':<30} {'Multibagger':<30}")
        print("-" * 100)
        print(f"{'Primary Value Metric':<40} {'Book/Price ≥ 0.40':<30} {'Book/Market ≥ 0.40':<30}")
        print(f"{'Profitability Metric':<40} {'OCF/Equity ≥ 10%':<30} {'Positive net income':<30}")
        print(f"{'FCF/Price Threshold':<40} {'≥ 3% (quality screen)':<30} {'≥ 5% (core filter)':<30}")
        print(f"{'Entry Timing':<40} {'No':<30} {'Yes (near lows, neg momentum)':<30}")
        print(f"{'Reinvestment Quality':<40} {'Bonus points':<30} {'Required filter':<30}")
        print()

        print("=" * 100)
        print("TOP HOLDINGS COMPARISON")
        print("=" * 100)
        print()

        print("AVANTIS TSX TOP 10 (Core Holdings)")
        print("-" * 100)

        for i, candidate in enumerate(avantis_candidates[:10], 1):
            overlap = "⭐" if candidate.symbol in multibagger_symbols else "  "
            print(f"{i:2}. {overlap} {candidate.symbol:<12} {candidate.name:<40} Score: {candidate.factor_score:5.1f}")
            print(f"      Book/Price: {candidate.book_to_price:.3f} | Cash Prof: {candidate.cash_profitability:.2%} | FCF/P: {candidate.fcf_price_ratio:.2%}" if candidate.fcf_price_ratio else "")

        print()
        print("MULTIBAGGER TOP 10 (Satellite Holdings)")
        print("-" * 100)

        for i, (stock, fundamentals, score) in enumerate(multibagger_results[:10], 1):
            avantis_symbols = {c.symbol for c in avantis_candidates}
            overlap = "⭐" if stock.symbol in avantis_symbols else "  "
            print(f"{i:2}. {overlap} {stock.symbol:<12} {stock.name:<40} Score: {score:5.1f}")
            print(f"      FCF/Price: {fundamentals.fcf_price_ratio:.2%} | Book/Market: {fundamentals.book_to_market:.3f}")

        print()
        print("⭐ = Stock appears in both strategies")
        print()

        # Portfolio recommendation
        print("=" * 100)
        print("💡 RECOMMENDED PORTFOLIO CONSTRUCTION")
        print("=" * 100)
        print()

        print("TIERED APPROACH (Balances diversification + conviction):")
        print()
        print("  📊 CORE (60-70%): Avantis TSX Strategy")
        print("     • Hold 15-20 stocks")
        print("     • Equal weight or factor-weighted")
        print("     • Rebalance quarterly")
        print("     • Lower volatility, consistent factor exposure")
        print()
        print("  🎯 SATELLITE (30-40%): Multibagger Strategy")
        print("     • Hold 5-10 stocks")
        print("     • Higher conviction, score-weighted")
        print("     • Rebalance opportunistically")
        print("     • Higher risk/reward, 10x potential")
        print()

        print("RATIONALE:")
        print("  • Core provides stable factor returns (like Avantis ETFs)")
        print("  • Satellite captures multibagger opportunities (Yartseva's edge)")
        print("  • Combined: ~25-30 total holdings with smart diversification")
        print("  • Risk-managed: Core cushions satellite volatility")
        print()

        print("NEXT STEPS:")
        print("  1. Run detailed Avantis screening:")
        print("     python scripts/screen-avantis-tsx.py portfolio")
        print()
        print("  2. Run detailed Multibagger screening:")
        print("     python scripts/screen-multibaggers.py 10")
        print()
        print("  3. Get Claude's analysis on overlapping stocks (⭐)")
        print("     These are highest conviction - appear in both strategies!")
        print()


if __name__ == "__main__":
    main()
