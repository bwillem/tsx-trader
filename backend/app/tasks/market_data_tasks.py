from celery import shared_task
from app.database import get_db_context
from app.models.stock import Stock
from app.services.market_data import AlphaVantageService


@shared_task(name="app.tasks.market_data_tasks.update_market_data")
def update_market_data():
    """Update market data for all active stocks"""
    print("Starting market data update...")

    with get_db_context() as db:
        # Get all active stocks
        stocks = db.query(Stock).filter(Stock.is_active == True).all()

        if not stocks:
            print("No active stocks found")
            return {"status": "no_stocks"}

        av_service = AlphaVantageService()
        results = {}

        for stock in stocks:
            try:
                success = av_service.update_stock_data(db, stock)
                results[stock.symbol] = "success" if success else "failed"

                # Rate limiting: 5 calls per minute for Alpha Vantage free tier
                import time

                time.sleep(12)  # 12 seconds between calls
            except Exception as e:
                print(f"Error updating {stock.symbol}: {e}")
                results[stock.symbol] = f"error: {str(e)}"

        print(f"Market data update complete: {results}")
        return results


@shared_task(name="app.tasks.market_data_tasks.update_single_stock")
def update_single_stock(symbol: str):
    """Update market data for a single stock

    Args:
        symbol: Stock symbol to update
    """
    print(f"Updating market data for {symbol}...")

    with get_db_context() as db:
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()

        if not stock:
            # Create stock if it doesn't exist
            stock = Stock(symbol=symbol, name=symbol, exchange="TSX")
            db.add(stock)
            db.flush()

        av_service = AlphaVantageService()
        success = av_service.update_stock_data(db, stock)

        return {"symbol": symbol, "status": "success" if success else "failed"}


@shared_task(name="app.tasks.market_data_tasks.update_fundamental_data")
def update_fundamental_data(batch_size: int = 6):
    """Update fundamental data for active stocks in batches

    Alpha Vantage free tier limits:
    - 25 API calls per day
    - 5 API calls per minute
    - Each stock needs 4 calls (overview, income, balance, cash flow)
    - Therefore: max 6 stocks per day (6 × 4 = 24 calls)

    This function processes stocks that haven't been updated recently first,
    allowing gradual population over multiple days.

    Args:
        batch_size: Number of stocks to process (default 6 for free tier)

    Fetches quarterly fundamental data and calculates key metrics:
    - FCF/Price (free cash flow yield) - STRONGEST PREDICTOR
    - Book-to-Market ratio - value factor
    - ROA - profitability
    - Asset growth vs EBITDA growth - reinvestment quality
    """
    print(f"Starting fundamental data update (batch size: {batch_size})...")

    from datetime import datetime, timedelta
    from sqlalchemy import func, or_
    from app.models.fundamentals import FundamentalDataQuarterly

    with get_db_context() as db:
        # Get stocks that haven't been updated recently (or never)
        # Priority: stocks with no data > stocks with old data

        # Find stocks with no fundamental data
        stocks_without_data = (
            db.query(Stock)
            .outerjoin(Stock.fundamental_data)
            .filter(
                Stock.is_active == True,
                FundamentalDataQuarterly.id.is_(None)
            )
            .order_by(Stock.symbol)
            .limit(batch_size)
            .all()
        )

        stocks_to_update = stocks_without_data

        # If we need more stocks to fill the batch, get stocks with old data
        if len(stocks_to_update) < batch_size:
            remaining = batch_size - len(stocks_to_update)

            # Get stocks with data older than 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)

            subquery = (
                db.query(
                    FundamentalDataQuarterly.stock_id,
                    func.max(FundamentalDataQuarterly.updated_at).label('last_update')
                )
                .group_by(FundamentalDataQuarterly.stock_id)
                .subquery()
            )

            stocks_with_old_data = (
                db.query(Stock)
                .join(
                    subquery,
                    Stock.id == subquery.c.stock_id
                )
                .filter(
                    Stock.is_active == True,
                    subquery.c.last_update < week_ago,
                    ~Stock.id.in_([s.id for s in stocks_without_data])
                )
                .order_by(subquery.c.last_update)
                .limit(remaining)
                .all()
            )

            stocks_to_update.extend(stocks_with_old_data)

        if not stocks_to_update:
            print("No stocks need updating (all updated within last 7 days)")
            return {
                "status": "up_to_date",
                "processed": 0,
                "message": "All stocks have recent data"
            }

        print(f"\nProcessing {len(stocks_to_update)} stocks...")
        print(f"Stocks: {', '.join(s.symbol for s in stocks_to_update)}")

        av_service = AlphaVantageService()
        results = {
            "processed": 0,
            "success": [],
            "failed": [],
            "errors": {}
        }

        for stock in stocks_to_update:
            try:
                print(f"\n--- Processing {stock.symbol} ---")
                success = av_service.update_fundamental_data_quarterly(db, stock)

                if success:
                    results["success"].append(stock.symbol)
                    results["processed"] += 1
                    print(f"✓ Successfully updated {stock.symbol}")
                else:
                    results["failed"].append(stock.symbol)
                    print(f"✗ Failed to update {stock.symbol}")

                # Note: update_fundamental_data_quarterly already includes rate limiting
                # (4 API calls with 13 sec delays = ~52 sec per stock)

            except Exception as e:
                error_msg = str(e)
                print(f"✗ Error updating {stock.symbol}: {error_msg}")
                results["failed"].append(stock.symbol)
                results["errors"][stock.symbol] = error_msg

        print(f"\n{'='*60}")
        print(f"Fundamental data update complete:")
        print(f"  Processed: {results['processed']} stocks")
        print(f"  Success: {len(results['success'])} stocks")
        print(f"  Failed: {len(results['failed'])} stocks")

        if results['success']:
            print(f"\n  ✓ Updated: {', '.join(results['success'])}")
        if results['failed']:
            print(f"\n  ✗ Failed: {', '.join(results['failed'])}")

        print(f"{'='*60}")

        return results


@shared_task(name="app.tasks.market_data_tasks.update_single_stock_fundamentals")
def update_single_stock_fundamentals(symbol: str):
    """Update fundamental data for a single stock

    Args:
        symbol: Stock symbol to update
    """
    print(f"Updating fundamental data for {symbol}...")

    with get_db_context() as db:
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()

        if not stock:
            return {"symbol": symbol, "status": "error", "error": "Stock not found"}

        av_service = AlphaVantageService()
        success = av_service.update_fundamental_data_quarterly(db, stock)

        return {"symbol": symbol, "status": "success" if success else "failed"}
