#!/usr/bin/env python3
"""
Discover and update TSX stocks for multibagger screening.

This script can:
1. Discover new stocks in the $300M-$2B range
2. Review existing stocks and deactivate those outside range
3. Full refresh (both discovery and review)
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.services.stock_discovery import TSXStockDiscovery


def discover_new_stocks(max_new: int = 50):
    """Discover and add new TSX stocks"""
    db = SessionLocal()

    try:
        print("=== TSX STOCK DISCOVERY ===\n")
        print("This will check potential TSX small caps and add those in the")
        print("$300M-$2B market cap range (multibagger sweet spot).\n")

        discovery = TSXStockDiscovery(
            min_market_cap=300_000_000,
            max_market_cap=2_000_000_000,
            include_large_caps=True,
            rate_limit_delay=13,
        )

        stats = discovery.discover_and_update(
            db=db,
            symbol_list=None,  # Uses default list
            max_new_stocks=max_new,
        )

        # Show results
        if stats["in_range"]:
            print(f"\n{'='*60}")
            print(f"NEW SMALL CAPS ADDED ({len(stats['in_range'])}):")
            print(f"{'='*60}")
            for stock in stats["in_range"]:
                print(f"  {stock['symbol']:<10} ${stock['market_cap']:>12,.0f}  {stock['name']}")
                print(f"             Sector: {stock['sector']}")

        if stats["deactivated"] > 0:
            print(f"\n{'='*60}")
            print(f"STOCKS DEACTIVATED ({stats['deactivated']}):")
            print(f"{'='*60}")
            for stock in stats["out_of_range"]:
                if stock.get("reason") in ["grew too large", "became too small"]:
                    print(f"  {stock['symbol']:<10} ${stock['market_cap']:>12,.0f}  ({stock['reason']})")

        print(f"\n{'='*60}")
        print("NEXT STEPS:")
        print(f"{'='*60}")
        print("1. Fetch fundamental data for new stocks:")
        print("   docker-compose exec backend python -c \"")
        print("   from app.database import SessionLocal")
        print("   from app.tasks.market_data_tasks import update_fundamental_data")
        print("   update_fundamental_data()")
        print("   \"")
        print("\n2. Run multibagger screening:")
        print("   docker-compose exec backend python scripts/screen-multibaggers.py")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def review_existing_stocks():
    """Review existing stocks and update their status"""
    db = SessionLocal()

    try:
        print("=== REVIEWING EXISTING STOCKS ===\n")
        print("This will check all active stocks and deactivate those that")
        print("are no longer in the $300M-$2B range.\n")

        discovery = TSXStockDiscovery(
            min_market_cap=300_000_000,
            max_market_cap=2_000_000_000,
            include_large_caps=True,
            rate_limit_delay=13,
        )

        stats = discovery.review_existing_stocks(db)

        # Show deactivated stocks
        if stats["deactivated"] > 0:
            print(f"\n{'='*60}")
            print(f"STOCKS DEACTIVATED ({stats['deactivated']}):")
            print(f"{'='*60}")
            for detail in stats["details"]:
                print(f"  {detail['symbol']:<10} ${detail['market_cap']:>12,.0f}  ({detail['reason']})")

        print(f"\n{'='*60}")
        print("Stock universe is now up to date!")
        print(f"{'='*60}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def full_refresh():
    """Full refresh: review existing + discover new"""
    print("=== FULL STOCK UNIVERSE REFRESH ===\n")
    print("This will:")
    print("1. Review all existing stocks and update their status")
    print("2. Discover and add new stocks in the multibagger range\n")
    print("This may take 10-30 minutes depending on API rate limits.\n")

    confirm = input("Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return

    # Step 1: Review existing
    print("\n" + "="*60)
    print("STEP 1: REVIEWING EXISTING STOCKS")
    print("="*60 + "\n")
    review_existing_stocks()

    # Step 2: Discover new
    print("\n" + "="*60)
    print("STEP 2: DISCOVERING NEW STOCKS")
    print("="*60 + "\n")
    discover_new_stocks(max_new=50)

    print("\n" + "="*60)
    print("FULL REFRESH COMPLETE")
    print("="*60)


def show_stats():
    """Show current stock universe statistics"""
    db = SessionLocal()

    try:
        discovery = TSXStockDiscovery()
        stats = discovery.get_discovery_stats(db)

        print("=== STOCK UNIVERSE STATISTICS ===\n")
        print(f"Total stocks:    {stats['total_stocks']}")
        print(f"Active stocks:   {stats['active_stocks']}")
        print(f"Inactive stocks: {stats['inactive_stocks']}")
        print(f"TSX stocks:      {stats['tsx_stocks']}")
        print(f"Last updated:    {stats['last_updated']}")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "discover":
            max_new = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            discover_new_stocks(max_new)

        elif command == "review":
            review_existing_stocks()

        elif command == "refresh":
            full_refresh()

        elif command == "stats":
            show_stats()

        else:
            print(f"Unknown command: {command}")
            print("\nUsage:")
            print("  python discover-stocks.py discover [max_new]  - Discover new stocks")
            print("  python discover-stocks.py review              - Review existing stocks")
            print("  python discover-stocks.py refresh             - Full refresh (both)")
            print("  python discover-stocks.py stats               - Show statistics")

    else:
        print("TSX Stock Discovery - Keep your multibagger universe fresh\n")
        print("Usage:")
        print("  python scripts/discover-stocks.py discover [max_new]")
        print("    Discover and add new TSX stocks in the $300M-$2B range")
        print("    Optional: max_new = maximum number of new stocks to add (default 50)")
        print()
        print("  python scripts/discover-stocks.py review")
        print("    Review all existing stocks and deactivate those outside range")
        print()
        print("  python scripts/discover-stocks.py refresh")
        print("    Full refresh: review existing + discover new (recommended monthly)")
        print()
        print("  python scripts/discover-stocks.py stats")
        print("    Show current stock universe statistics")
        print()
        print("Examples:")
        print("  python scripts/discover-stocks.py discover 20")
        print("  python scripts/discover-stocks.py review")
        print("  python scripts/discover-stocks.py refresh")
