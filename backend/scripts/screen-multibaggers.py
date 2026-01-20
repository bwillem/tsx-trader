#!/usr/bin/env python3
"""
Screen for potential multibagger stocks using Yartseva's criteria.

This script applies the research findings from "The Alchemy of Multibagger Stocks"
to identify TSX stocks with the highest potential for 10x+ returns.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.services.screening import MultibaggerScreener


def screen_multibaggers(limit: int = 20, show_stats: bool = True):
    """Run multibagger screening

    Args:
        limit: Maximum number of results to show
        show_stats: Whether to show screening statistics
    """
    db = SessionLocal()

    try:
        print("=== MULTIBAGGER STOCK SCREENER ===")
        print("Based on Yartseva (2025) research\n")

        # Initialize screener with Yartseva's criteria
        screener = MultibaggerScreener(
            min_fcf_price_ratio=0.05,  # 5% FCF yield minimum
            min_book_to_market=0.40,   # Yartseva's threshold
            min_market_cap=300_000_000,  # $300M
            max_market_cap=2_000_000_000,  # $2B (small cap)
            require_profitability=True,
            exclude_negative_equity=True,
            require_reinvestment_quality=False,  # Optional (needs 2+ years data)
        )

        # Show statistics if requested
        if show_stats:
            print("SCREENING STATISTICS:")
            stats = screener.get_screening_stats(db)
            print(f"  Total stocks with fundamentals: {stats['total_stocks_with_fundamentals']}")
            print(f"  Passing FCF/Price filter (≥5%):  {stats['passing_fcf_filter']}")
            print(f"  Passing B/M filter (≥0.40):      {stats['passing_bm_filter']}")
            print(f"  Passing size filter ($300M-$2B): {stats['passing_size_filter']}")
            print(f"  Passing profitability filter:    {stats['passing_profitability_filter']}")
            print(f"  Passing ALL filters:             {stats['passing_all_filters']}")

            if stats['passing_all_filters'] > 0:
                print(f"\n  Average metrics (passing stocks):")
                print(f"    FCF/Price:    {stats['avg_fcf_price_ratio']:.2%}")
                print(f"    Book/Market:  {stats['avg_book_to_market']:.2f}")
                print(f"    ROA:          {stats['avg_roa']:.2%}")
                print(f"    Market Cap:   ${stats['avg_market_cap']:,.0f}")

            print("\n" + "="*80 + "\n")

        # Run screening
        print(f"SCREENING RESULTS (Top {limit}):\n")
        candidates = screener.screen(db, limit=limit, include_technical=True)

        if not candidates:
            print("❌ No stocks found matching the multibagger criteria")
            print("\nPossible reasons:")
            print("  1. No fundamental data in database (run: python scripts/test-fundamentals.py)")
            print("  2. Criteria too strict (try lowering min_fcf_price_ratio or min_book_to_market)")
            print("  3. Most TSX stocks don't meet small cap requirement")
            return

        print(f"Found {len(candidates)} potential multibagger candidates\n")
        print("="*80)

        for i, candidate in enumerate(candidates, 1):
            print(f"\n{i}. {candidate.symbol} - {candidate.name}")
            print(f"   Sector: {candidate.sector}")
            print(f"   MULTIBAGGER SCORE: {candidate.multibagger_score:.1f}/100\n")

            print(f"   KEY METRICS (Yartseva's predictors):")
            print(f"     FCF/Price:       {candidate.fcf_price_ratio:.2%} ⭐ STRONGEST")
            print(f"     Book/Market:     {candidate.book_to_market:.2f} {'✓' if candidate.book_to_market > 0.40 else '⚠'}")
            print(f"     ROA:             {candidate.roa:.2%}")
            print(f"     EBITDA Margin:   {candidate.ebitda_margin:.2%}")

            print(f"\n   SIZE & PROFITABILITY:")
            print(f"     Market Cap:      ${candidate.market_cap:,.0f}")
            print(f"     Profitable:      {'✓ Yes' if candidate.is_profitable else '✗ No'}")

            if candidate.asset_growth_rate is not None and candidate.ebitda_growth_rate is not None:
                print(f"\n   GROWTH QUALITY:")
                print(f"     Asset Growth:    {candidate.asset_growth_rate:.1%}")
                print(f"     EBITDA Growth:   {candidate.ebitda_growth_rate:.1%}")
                print(f"     Reinvestment:    {'✓ Good' if candidate.reinvestment_quality_flag else '⚠ Poor'}")

            if candidate.current_price:
                print(f"\n   TECHNICAL TIMING:")
                print(f"     Current Price:   ${candidate.current_price:.2f}")
                if candidate.distance_from_52w_high is not None:
                    print(f"     vs 52w High:     {candidate.distance_from_52w_high:.1%}")
                if candidate.distance_from_52w_low is not None:
                    print(f"     vs 52w Low:      +{candidate.distance_from_52w_low:.1%}")
                if candidate.momentum_6m is not None:
                    print(f"     6m Momentum:     {candidate.momentum_6m:.1%} {'✓ Negative (good)' if candidate.momentum_6m < 0 else ''}")

            print("\n" + "-"*80)

        print("\n" + "="*80)
        print("\nNOTE: These are SCREENING RESULTS, not investment recommendations.")
        print("Yartseva's research shows these factors predict 10x returns, but:")
        print("  - Individual stocks may not perform as expected")
        print("  - Past performance doesn't guarantee future results")
        print("  - Always do your own due diligence")
        print("  - Consider diversification and risk management")
        print("\nRecommended next steps:")
        print("  1. Review Claude's analysis for these symbols")
        print("  2. Check technical timing signals (buy near 52-week lows)")
        print("  3. Monitor for entry points")
        print("  4. Set stop losses at 5-10% below entry")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    show_stats = "--no-stats" not in sys.argv

    screen_multibaggers(limit=limit, show_stats=show_stats)
