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
