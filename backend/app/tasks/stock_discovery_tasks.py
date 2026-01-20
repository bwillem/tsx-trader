from celery import shared_task
from app.database import get_db_context
from app.services.stock_discovery import TSXStockDiscovery


@shared_task(name="app.tasks.stock_discovery_tasks.discover_new_stocks")
def discover_new_stocks(max_new_stocks: int = 50):
    """Discover and add new TSX stocks that fit multibagger criteria

    This task:
    1. Checks a curated list of potential TSX small caps
    2. Fetches market caps from Alpha Vantage
    3. Adds stocks in the $300M-$2B range
    4. Keeps some blue chips for diversification

    Args:
        max_new_stocks: Maximum number of new stocks to add (default 50)

    Returns:
        Dictionary with discovery statistics
    """
    print("Starting stock discovery...")

    with get_db_context() as db:
        discovery = TSXStockDiscovery(
            min_market_cap=300_000_000,  # $300M
            max_market_cap=2_000_000_000,  # $2B
            include_large_caps=True,  # Keep blue chips
            rate_limit_delay=13,  # Alpha Vantage free tier
        )

        stats = discovery.discover_and_update(
            db=db,
            symbol_list=None,  # Uses default candidate list
            max_new_stocks=max_new_stocks,
        )

        return stats


@shared_task(name="app.tasks.stock_discovery_tasks.review_existing_stocks")
def review_existing_stocks():
    """Review all existing stocks and update their active status

    This task:
    1. Checks market caps of all active stocks
    2. Deactivates stocks that grew too large (>$2B)
    3. Deactivates stocks that became too small (<$300M)
    4. Keeps blue chips regardless of size

    Returns:
        Dictionary with review statistics
    """
    print("Starting stock review...")

    with get_db_context() as db:
        discovery = TSXStockDiscovery(
            min_market_cap=300_000_000,
            max_market_cap=2_000_000_000,
            include_large_caps=True,
            rate_limit_delay=13,
        )

        stats = discovery.review_existing_stocks(db)

        return stats


@shared_task(name="app.tasks.stock_discovery_tasks.full_universe_refresh")
def full_universe_refresh():
    """Full refresh of stock universe

    Runs both discovery and review tasks sequentially:
    1. Review existing stocks (update status)
    2. Discover new stocks (add candidates)

    This should be run weekly or monthly to keep the universe fresh.

    Returns:
        Dictionary with combined statistics
    """
    print("Starting full universe refresh...")

    with get_db_context() as db:
        discovery = TSXStockDiscovery(
            min_market_cap=300_000_000,
            max_market_cap=2_000_000_000,
            include_large_caps=True,
            rate_limit_delay=13,
        )

        # Step 1: Review existing stocks
        print("\n=== STEP 1: Review Existing Stocks ===")
        review_stats = discovery.review_existing_stocks(db)

        # Step 2: Discover new stocks
        print("\n=== STEP 2: Discover New Stocks ===")
        discovery_stats = discovery.discover_and_update(
            db=db,
            symbol_list=None,
            max_new_stocks=50,
        )

        # Step 3: Get final stats
        print("\n=== STEP 3: Final Statistics ===")
        final_stats = discovery.get_discovery_stats(db)

        return {
            "review": review_stats,
            "discovery": discovery_stats,
            "final": final_stats,
        }
